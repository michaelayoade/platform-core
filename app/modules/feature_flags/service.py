from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from redis import Redis

from app.modules.feature_flags.models import (
    FeatureFlag, FeatureFlagCreate, FeatureFlagUpdate
)


class FeatureFlagService:
    """
    Service for managing feature flags.
    """
    
    # Redis key patterns
    FLAG_KEY_PATTERN = "feature_flag:{key}"
    
    @staticmethod
    async def create_feature_flag(db: Session, flag: FeatureFlagCreate) -> FeatureFlag:
        """
        Create a new feature flag.
        """
        db_flag = FeatureFlag(
            key=flag.key,
            name=flag.name,
            description=flag.description,
            enabled=flag.enabled,
            rules=flag.rules
        )
        
        try:
            db.add(db_flag)
            db.commit()
            db.refresh(db_flag)
            return db_flag
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Feature flag with key '{flag.key}' already exists"
            )
    
    @staticmethod
    async def get_feature_flags(db: Session, skip: int = 0, limit: int = 100) -> List[FeatureFlag]:
        """
        Get all feature flags.
        """
        return db.query(FeatureFlag).offset(skip).limit(limit).all()
    
    @staticmethod
    async def get_feature_flag_by_key(db: Session, key: str) -> Optional[FeatureFlag]:
        """
        Get a feature flag by key.
        """
        return db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    
    @staticmethod
    async def update_feature_flag(
        db: Session, key: str, flag: FeatureFlagUpdate
    ) -> FeatureFlag:
        """
        Update a feature flag.
        """
        db_flag = await FeatureFlagService.get_feature_flag_by_key(db, key)
        if not db_flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag with key '{key}' not found"
            )
        
        # Update fields if provided
        if flag.name is not None:
            db_flag.name = flag.name
        
        if flag.description is not None:
            db_flag.description = flag.description
        
        if flag.enabled is not None:
            db_flag.enabled = flag.enabled
        
        if flag.rules is not None:
            db_flag.rules = flag.rules
        
        db.commit()
        db.refresh(db_flag)
        
        return db_flag
    
    @staticmethod
    async def delete_feature_flag(db: Session, key: str) -> bool:
        """
        Delete a feature flag.
        """
        db_flag = await FeatureFlagService.get_feature_flag_by_key(db, key)
        if not db_flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag with key '{key}' not found"
            )
        
        db.delete(db_flag)
        db.commit()
        
        return True
    
    @classmethod
    async def cache_feature_flag(cls, redis: Redis, key: str, enabled: bool) -> bool:
        """
        Cache a feature flag in Redis.
        """
        redis_key = cls.FLAG_KEY_PATTERN.format(key=key)
        return redis.set(redis_key, str(int(enabled)))
    
    @classmethod
    async def get_cached_feature_flag(cls, redis: Redis, key: str) -> Optional[bool]:
        """
        Get a cached feature flag from Redis.
        """
        redis_key = cls.FLAG_KEY_PATTERN.format(key=key)
        value = redis.get(redis_key)
        if value is None:
            return None
        return value == "1"
    
    @classmethod
    async def invalidate_feature_flag_cache(cls, redis: Redis, key: str) -> bool:
        """
        Invalidate a cached feature flag.
        """
        redis_key = cls.FLAG_KEY_PATTERN.format(key=key)
        return redis.delete(redis_key) > 0
    
    @staticmethod
    async def is_enabled_for_user(
        db: Session, 
        key: str, 
        user_id: Optional[str] = None,
        groups: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a feature flag is enabled for a specific user.
        """
        db_flag = await FeatureFlagService.get_feature_flag_by_key(db, key)
        if not db_flag:
            return False
        
        # If flag is disabled globally, return False
        if not db_flag.enabled:
            return False
        
        # If no rules, the flag is enabled for everyone
        if not db_flag.rules:
            return True
        
        # Check user targeting rules
        rules = db_flag.rules
        
        # Check user ID targeting
        if user_id and "users" in rules:
            if user_id in rules["users"]:
                return True
        
        # Check group targeting
        if groups and "groups" in rules:
            if any(group in rules["groups"] for group in groups):
                return True
        
        # Check attribute targeting (e.g., {"country": "US", "role": "admin"})
        if attributes and "attributes" in rules:
            rule_attributes = rules["attributes"]
            for key, value in rule_attributes.items():
                if key in attributes and attributes[key] == value:
                    return True
        
        # Check percentage rollout
        if user_id and "percentage" in rules:
            # Simple hash-based percentage rollout
            percentage = rules["percentage"]
            if percentage >= 100:
                return True
            
            if percentage <= 0:
                return False
            
            # Hash the user ID to get a consistent value between 0-99
            hash_value = hash(user_id) % 100
            return hash_value < percentage
        
        # Default to the global flag value
        return db_flag.enabled
