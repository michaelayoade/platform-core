import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

import redis
from sqlalchemy.orm import Session

from .models import (
    FeatureFlag,
    FeatureFlagCreate,
    FeatureFlagUpdate,
)

logger = logging.getLogger(__name__)

# Redis key prefix for feature flags
FEATURE_FLAG_CACHE_PREFIX = "feature_flag:"
# Cache TTL (e.g., 5 minutes)
FEATURE_FLAG_CACHE_TTL = timedelta(minutes=5)


class FeatureFlagsService:
    """Service layer for managing feature flags and their evaluation."""

    @staticmethod
    def _get_cache_key(flag_key: str) -> str:
        return f"{FEATURE_FLAG_CACHE_PREFIX}{flag_key}"

    # --- Flag CRUD Operations ---

    @staticmethod
    def create_feature_flag(
        db: Session, redis_client: redis.Redis, flag_in: FeatureFlagCreate
    ) -> FeatureFlag:
        """Creates a new feature flag."""
        existing = db.query(FeatureFlag).filter(FeatureFlag.key == flag_in.key).first()
        if existing:
            raise ValueError(f"Feature flag with key '{flag_in.key}' already exists.")

        db_flag = FeatureFlag(**flag_in.dict())
        db.add(db_flag)
        db.commit()
        db.refresh(db_flag)
        logger.info(f"Feature flag created: Key='{db_flag.key}', ID={db_flag.id}")

        # Invalidate cache (though unlikely to exist)
        FeatureFlagsService.invalidate_flag_cache(redis_client, db_flag.key)
        return db_flag

    @staticmethod
    def get_feature_flag_by_key(db: Session, flag_key: str) -> Optional[FeatureFlag]:
        """Retrieves a feature flag by its key."""
        return db.query(FeatureFlag).filter(FeatureFlag.key == flag_key).first()

    @staticmethod
    def get_feature_flags(
        db: Session, skip: int = 0, limit: int = 100
    ) -> List[FeatureFlag]:
        """Retrieves a list of feature flags."""
        return db.query(FeatureFlag).offset(skip).limit(limit).all()

    @staticmethod
    def update_feature_flag(
        db: Session,
        redis_client: redis.Redis,
        flag_key: str,
        flag_update: FeatureFlagUpdate,
    ) -> Optional[FeatureFlag]:
        """Updates an existing feature flag."""
        db_flag = FeatureFlagsService.get_feature_flag_by_key(db, flag_key)
        if not db_flag:
            return None

        update_data = flag_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_flag, key, value)

        db.commit()
        db.refresh(db_flag)
        logger.info(f"Feature flag updated: Key='{db_flag.key}', Changes={update_data}")

        # Invalidate cache if relevant fields changed
        if "enabled" in update_data or "description" in update_data:
            FeatureFlagsService.invalidate_flag_cache(redis_client, flag_key)

        return db_flag

    @staticmethod
    def delete_feature_flag(
        db: Session, redis_client: redis.Redis, flag_key: str
    ) -> bool:
        """Deletes a feature flag."""
        db_flag = FeatureFlagsService.get_feature_flag_by_key(db, flag_key)
        if not db_flag:
            return False

        db.delete(db_flag)
        db.commit()
        logger.info(f"Feature flag deleted: Key='{flag_key}'")

        # Invalidate cache
        FeatureFlagsService.invalidate_flag_cache(redis_client, flag_key)
        return True

    # --- Flag Evaluation Logic ---

    @staticmethod
    def is_feature_enabled(
        db: Session, redis_client: redis.Redis, flag_key: str, context: Dict[str, Any]
    ) -> bool:
        """Checks if a feature flag is enabled for the given context."""
        # 1. Check Cache
        cached_flag = FeatureFlagsService._get_flag_from_cache(redis_client, flag_key)
        if cached_flag is not None:
            logger.debug(f"Cache hit for feature flag '{flag_key}'")
            # Evaluate rules based on cached data
            return FeatureFlagsService._evaluate_rules(
                globally_enabled=cached_flag["enabled"],
                rules=cached_flag.get("rules"),
                context=context,
            )

        # 2. Cache miss - Fetch from DB
        logger.debug(f"Cache miss for feature flag '{flag_key}'. Fetching from DB.")
        db_flag = db.query(FeatureFlag).filter(FeatureFlag.key == flag_key).first()

        if not db_flag:
            # Flag doesn't exist
            logger.warning(f"Feature flag '{flag_key}' not found during evaluation.")
            raise ValueError(f"Feature flag '{flag_key}' not found.")

        # 3. Evaluate Rules
        is_enabled = FeatureFlagsService._evaluate_rules(
            globally_enabled=db_flag.enabled, rules=db_flag.rules, context=context
        )

        # 4. Update Cache
        FeatureFlagsService._cache_flag(redis_client, db_flag)

        return is_enabled

    @staticmethod
    def _evaluate_rules(
        globally_enabled: bool, rules: Optional[Dict[str, Any]], context: Dict[str, Any]
    ) -> bool:
        """Evaluates targeting rules against the provided context."""
        if not globally_enabled:
            return False  # If globally disabled, rules don't matter

        if not rules:
            # No specific rules, default to globally enabled state
            return True

        # Simple rule evaluation (example: check user_id or group_id)
        # TODO: Implement more sophisticated rule engine (e.g., percentage rollout, attribute matching)

        user_id = context.get("user_id")
        group_id = context.get("group_id")

        # Check user targeting
        allowed_users = rules.get("allowed_users", [])
        if user_id and user_id in allowed_users:
            return True

        # Check group targeting
        allowed_groups = rules.get("allowed_groups", [])
        if group_id and group_id in allowed_groups:
            return True

        # Check percentage rollout (simple example)
        percentage = rules.get("percentage")
        if percentage is not None and user_id:
            # Basic hash-based rollout (needs a stable hashing function)
            import hashlib

            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            if (user_hash % 100) < percentage:
                return True

        # If no rules matched, and the flag is globally enabled BUT has rules,
        # it means the user doesn't fit the specific targeting. Default to false.
        # If globally enabled AND NO rules, default is true (handled above).
        return False

    # --- Cache Management ---

    @staticmethod
    def _get_flag_from_cache(
        redis_client: redis.Redis, flag_key: str
    ) -> Optional[Dict]:
        """Retrieves flag data from Redis cache."""
        cache_key = FeatureFlagsService._get_cache_key(flag_key)
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                import json

                return json.loads(cached_data)
        except redis.RedisError as e:
            logger.error(f"Redis error getting cache for '{flag_key}': {e}")
        return None

    @staticmethod
    def _cache_flag(redis_client: redis.Redis, flag: FeatureFlag):
        """Stores flag data in Redis cache."""
        cache_key = FeatureFlagsService._get_cache_key(flag.key)
        try:
            import json

            flag_data = {
                "key": flag.key,
                "enabled": flag.enabled,
                "rules": flag.rules,
                "updated_at": flag.updated_at.isoformat() if flag.updated_at else None,
            }
            redis_client.set(
                cache_key, json.dumps(flag_data), ex=FEATURE_FLAG_CACHE_TTL
            )
            logger.debug(f"Cached feature flag '{flag.key}'")
        except redis.RedisError as e:
            logger.error(f"Redis error setting cache for '{flag.key}': {e}")
        except TypeError as e:
            logger.error(f"Serialization error caching flag '{flag.key}': {e}")

    @staticmethod
    def invalidate_flag_cache(redis_client: redis.Redis, flag_key: str):
        """Removes a flag from the Redis cache."""
        cache_key = FeatureFlagsService._get_cache_key(flag_key)
        try:
            redis_client.delete(cache_key)
            logger.info(f"Invalidated cache for feature flag '{flag_key}'")
        except redis.RedisError as e:
            logger.error(f"Redis error deleting cache for '{flag_key}': {e}")
