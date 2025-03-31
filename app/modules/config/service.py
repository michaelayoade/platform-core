from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from redis import Redis

from app.modules.config.models import (
    ConfigScope, ConfigItem, ConfigHistory,
    ConfigScopeCreate, ConfigItemCreate, ConfigItemUpdate
)


class ConfigService:
    """
    Service for managing configuration.
    """
    
    # Redis key patterns
    CONFIG_KEY_PATTERN = "config:{scope}:{key}"
    CONFIG_SCOPE_PATTERN = "config:{scope}:*"
    
    @staticmethod
    async def create_scope(db: Session, scope: ConfigScopeCreate) -> ConfigScope:
        """
        Create a new configuration scope.
        """
        db_scope = ConfigScope(
            name=scope.name,
            description=scope.description
        )
        
        try:
            db.add(db_scope)
            db.commit()
            db.refresh(db_scope)
            return db_scope
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Scope with name '{scope.name}' already exists"
            )
    
    @staticmethod
    async def get_scopes(db: Session, skip: int = 0, limit: int = 100) -> List[ConfigScope]:
        """
        Get all configuration scopes.
        """
        return db.query(ConfigScope).offset(skip).limit(limit).all()
    
    @staticmethod
    async def get_scope_by_name(db: Session, name: str) -> Optional[ConfigScope]:
        """
        Get a configuration scope by name.
        """
        return db.query(ConfigScope).filter(ConfigScope.name == name).first()
    
    @staticmethod
    async def get_scope_by_id(db: Session, scope_id: int) -> Optional[ConfigScope]:
        """
        Get a configuration scope by ID.
        """
        return db.query(ConfigScope).filter(ConfigScope.id == scope_id).first()
    
    @staticmethod
    async def create_config_item(
        db: Session, 
        scope_name: str, 
        config: ConfigItemCreate, 
        user_id: Optional[str] = None
    ) -> ConfigItem:
        """
        Create a new configuration item.
        """
        # Get scope
        scope = await ConfigService.get_scope_by_name(db, scope_name)
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scope '{scope_name}' not found"
            )
        
        # Create config item
        db_config = ConfigItem(
            key=config.key,
            value=config.value,
            description=config.description,
            is_secret=1 if config.is_secret else 0,
            scope_id=scope.id
        )
        
        try:
            db.add(db_config)
            db.commit()
            db.refresh(db_config)
            
            # Create initial history entry
            history = ConfigHistory(
                value=config.value,
                version=1,
                changed_by=user_id,
                config_id=db_config.id
            )
            db.add(history)
            db.commit()
            
            return db_config
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Config with key '{config.key}' already exists in scope '{scope_name}'"
            )
    
    @staticmethod
    async def get_config_items(
        db: Session, 
        scope_name: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ConfigItem]:
        """
        Get all configuration items for a scope.
        """
        scope = await ConfigService.get_scope_by_name(db, scope_name)
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scope '{scope_name}' not found"
            )
        
        return db.query(ConfigItem).filter(ConfigItem.scope_id == scope.id).offset(skip).limit(limit).all()
    
    @staticmethod
    async def get_config_item(db: Session, scope_name: str, key: str) -> Optional[ConfigItem]:
        """
        Get a configuration item by scope and key.
        """
        scope = await ConfigService.get_scope_by_name(db, scope_name)
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scope '{scope_name}' not found"
            )
        
        return db.query(ConfigItem).filter(
            ConfigItem.scope_id == scope.id,
            ConfigItem.key == key
        ).first()
    
    @staticmethod
    async def update_config_item(
        db: Session, 
        scope_name: str, 
        key: str, 
        config: ConfigItemUpdate, 
        user_id: Optional[str] = None
    ) -> ConfigItem:
        """
        Update a configuration item.
        """
        # Get config item
        db_config = await ConfigService.get_config_item(db, scope_name, key)
        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config with key '{key}' not found in scope '{scope_name}'"
            )
        
        # Create history entry before updating
        history = ConfigHistory(
            value=db_config.value,
            version=db_config.version,
            changed_by=user_id,
            config_id=db_config.id
        )
        db.add(history)
        
        # Update config item
        db_config.value = config.value
        db_config.version += 1
        
        if config.description is not None:
            db_config.description = config.description
        
        if config.is_secret is not None:
            db_config.is_secret = 1 if config.is_secret else 0
        
        db.commit()
        db.refresh(db_config)
        
        return db_config
    
    @staticmethod
    async def delete_config_item(db: Session, scope_name: str, key: str) -> bool:
        """
        Delete a configuration item.
        """
        # Get config item
        db_config = await ConfigService.get_config_item(db, scope_name, key)
        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config with key '{key}' not found in scope '{scope_name}'"
            )
        
        db.delete(db_config)
        db.commit()
        
        return True
    
    @staticmethod
    async def get_config_history(
        db: Session, 
        scope_name: str, 
        key: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ConfigHistory]:
        """
        Get history for a configuration item.
        """
        # Get config item
        db_config = await ConfigService.get_config_item(db, scope_name, key)
        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config with key '{key}' not found in scope '{scope_name}'"
            )
        
        return db.query(ConfigHistory).filter(
            ConfigHistory.config_id == db_config.id
        ).order_by(ConfigHistory.version.desc()).offset(skip).limit(limit).all()
    
    @classmethod
    async def cache_config(cls, redis: Redis, scope_name: str, key: str, value: str) -> bool:
        """
        Cache a configuration item in Redis.
        """
        redis_key = cls.CONFIG_KEY_PATTERN.format(scope=scope_name, key=key)
        return redis.set(redis_key, value)
    
    @classmethod
    async def get_cached_config(cls, redis: Redis, scope_name: str, key: str) -> Optional[str]:
        """
        Get a cached configuration item from Redis.
        """
        redis_key = cls.CONFIG_KEY_PATTERN.format(scope=scope_name, key=key)
        return redis.get(redis_key)
    
    @classmethod
    async def invalidate_config_cache(cls, redis: Redis, scope_name: str, key: str) -> bool:
        """
        Invalidate a cached configuration item.
        """
        redis_key = cls.CONFIG_KEY_PATTERN.format(scope=scope_name, key=key)
        return redis.delete(redis_key) > 0
    
    @classmethod
    async def invalidate_scope_cache(cls, redis: Redis, scope_name: str) -> int:
        """
        Invalidate all cached configuration items for a scope.
        """
        pattern = cls.CONFIG_SCOPE_PATTERN.format(scope=scope_name)
        keys = redis.keys(pattern)
        if not keys:
            return 0
        return redis.delete(*keys)
    
    @classmethod
    async def publish_config_update(cls, redis: Redis, scope_name: str, key: str) -> int:
        """
        Publish a configuration update event.
        """
        channel = f"config_updates:{scope_name}"
        message = f"{key}"
        return redis.publish(channel, message)
