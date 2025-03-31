from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from redis import Redis

from app.db.session import get_db
from app.db.redis import get_redis
from app.modules.feature_flags.models import (
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse,
    FeatureFlagCheck, FeatureFlagCheckResponse
)
from app.modules.feature_flags.service import FeatureFlagService
from app.modules.audit.service import AuditService
from app.utils.common import get_client_ip

router = APIRouter()


@router.post("/", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_feature_flag(
    flag: FeatureFlagCreate,
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Create a new feature flag.
    """
    # In a real app, we would extract the user ID from the JWT token
    # For now, we'll use the client IP as a placeholder
    user_id = get_client_ip(request)
    
    feature_flag = await FeatureFlagService.create_feature_flag(db, flag)
    
    # Cache the feature flag
    await FeatureFlagService.cache_feature_flag(redis, flag.key, flag.enabled)
    
    # Record audit log
    await AuditService.record_feature_flag_change(
        db, user_id, flag.key, None, flag.enabled, "create", user_id
    )
    
    return feature_flag


@router.get("/", response_model=List[FeatureFlagResponse])
async def get_feature_flags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all feature flags.
    """
    return await FeatureFlagService.get_feature_flags(db, skip, limit)


@router.get("/{key}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    key: str,
    db: Session = Depends(get_db)
):
    """
    Get a feature flag by key.
    """
    feature_flag = await FeatureFlagService.get_feature_flag_by_key(db, key)
    if not feature_flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag with key '{key}' not found"
        )
    return feature_flag


@router.put("/{key}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    key: str,
    flag: FeatureFlagUpdate,
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Update a feature flag.
    """
    # In a real app, we would extract the user ID from the JWT token
    # For now, we'll use the client IP as a placeholder
    user_id = get_client_ip(request)
    
    # Get current value for audit log
    current_flag = await FeatureFlagService.get_feature_flag_by_key(db, key)
    if not current_flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag with key '{key}' not found"
        )
    
    old_enabled = current_flag.enabled
    
    # Update the feature flag
    feature_flag = await FeatureFlagService.update_feature_flag(db, key, flag)
    
    # Update cache if enabled status changed
    if flag.enabled is not None:
        await FeatureFlagService.cache_feature_flag(redis, key, feature_flag.enabled)
    
    # Record audit log if enabled status changed
    if flag.enabled is not None and flag.enabled != old_enabled:
        await AuditService.record_feature_flag_change(
            db, user_id, key, old_enabled, feature_flag.enabled, "update", user_id
        )
    
    return feature_flag


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_flag(
    key: str,
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Delete a feature flag.
    """
    # In a real app, we would extract the user ID from the JWT token
    # For now, we'll use the client IP as a placeholder
    user_id = get_client_ip(request)
    
    # Get current value for audit log
    current_flag = await FeatureFlagService.get_feature_flag_by_key(db, key)
    if not current_flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag with key '{key}' not found"
        )
    
    # Delete the feature flag
    await FeatureFlagService.delete_feature_flag(db, key)
    
    # Invalidate cache
    await FeatureFlagService.invalidate_feature_flag_cache(redis, key)
    
    # Record audit log
    await AuditService.record_feature_flag_change(
        db, user_id, key, current_flag.enabled, None, "delete", user_id
    )


@router.post("/{key}/check", response_model=FeatureFlagCheckResponse)
async def check_feature_flag(
    key: str,
    check: FeatureFlagCheck,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Check if a feature flag is enabled for a specific user.
    """
    # Try to get from cache first
    cached_value = await FeatureFlagService.get_cached_feature_flag(redis, key)
    
    if cached_value is not None:
        # If cached value is False, return immediately
        if not cached_value:
            return FeatureFlagCheckResponse(key=key, enabled=False)
        
        # If cached value is True, we need to check user targeting rules
        enabled = await FeatureFlagService.is_enabled_for_user(
            db, key, check.user_id, check.groups, check.attributes
        )
        return FeatureFlagCheckResponse(key=key, enabled=enabled)
    
    # Not in cache, check database
    enabled = await FeatureFlagService.is_enabled_for_user(
        db, key, check.user_id, check.groups, check.attributes
    )
    
    # Cache the global flag status (not the user-specific result)
    feature_flag = await FeatureFlagService.get_feature_flag_by_key(db, key)
    if feature_flag:
        await FeatureFlagService.cache_feature_flag(redis, key, feature_flag.enabled)
    
    return FeatureFlagCheckResponse(key=key, enabled=enabled)
