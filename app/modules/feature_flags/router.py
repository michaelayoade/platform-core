import logging
from typing import List, Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.redis import get_redis_client
from app.db.session import get_db

from .models import FeatureFlagCreate, FeatureFlagResponse, FeatureFlagUpdate
from .service import FeatureFlagsService

router = APIRouter()
logger = logging.getLogger(__name__)

FEATURE_FLAG_TAG = "Feature Flags"


# --- Feature Flag Endpoints ---


@router.post(
    "/",
    response_model=FeatureFlagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Feature Flag",
    description="Creates a new feature flag.",
    tags=[FEATURE_FLAG_TAG],
)
async def create_feature_flag(
    flag_in: FeatureFlagCreate,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> FeatureFlagResponse:
    """Create a new feature flag definition."""
    try:
        flag = FeatureFlagsService.create_feature_flag(
            db, redis_client, flag_in=flag_in
        )
    except ValueError as e:
        logger.warning(f"Failed to create feature flag '{flag_in.key}': {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return flag


@router.get(
    "/",
    response_model=List[FeatureFlagResponse],
    summary="List Feature Flags",
    description="Retrieves a list of all defined feature flags.",
    tags=[FEATURE_FLAG_TAG],
)
async def list_feature_flags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[FeatureFlagResponse]:
    """Retrieve all feature flags with pagination."""
    flags = FeatureFlagsService.get_feature_flags(db, skip=skip, limit=limit)
    return flags


@router.get(
    "/{flag_key}",
    response_model=FeatureFlagResponse,
    summary="Get Feature Flag by Key",
    description="Retrieves details of a specific feature flag by its key.",
    tags=[FEATURE_FLAG_TAG],
)
async def get_feature_flag(
    flag_key: str,
    db: Session = Depends(get_db),
) -> FeatureFlagResponse:
    """Retrieve a single feature flag definition."""
    flag = FeatureFlagsService.get_feature_flag_by_key(db, flag_key)
    if not flag:
        logger.warning(f"Feature flag with key '{flag_key}' not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found"
        )
    return flag


@router.put(
    "/{flag_key}",
    response_model=FeatureFlagResponse,
    summary="Update Feature Flag",
    description="Updates an existing feature flag.",
    tags=[FEATURE_FLAG_TAG],
)
async def update_feature_flag(
    flag_key: str,
    flag_in: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> FeatureFlagResponse:
    """Update an existing feature flag's properties."""
    flag = FeatureFlagsService.update_feature_flag(
        db, redis_client, flag_key=flag_key, flag_update=flag_in
    )
    if not flag:
        logger.warning(f"Feature flag with key '{flag_key}' not found for update.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found"
        )
    return flag


@router.delete(
    "/{flag_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Feature Flag",
    description="Deletes a feature flag and its associated segments.",
    tags=[FEATURE_FLAG_TAG],
)
async def delete_feature_flag(
    flag_key: str,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> None:
    """Delete a feature flag and its segments."""
    deleted = FeatureFlagsService.delete_feature_flag(
        db, redis_client, flag_key=flag_key
    )
    if not deleted:
        logger.warning(f"Feature flag with key '{flag_key}' not found for deletion.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found"
        )
    return None  # Return 204 No Content


@router.get(
    "/evaluate/{flag_key}",
    response_model=bool,
    summary="Evaluate Feature Flag",
    description="Evaluates a feature flag for a given context (e.g., user ID, group).",
    tags=[FEATURE_FLAG_TAG],
)
async def evaluate_feature_flag(
    flag_key: str,
    user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    # Add other context attributes as needed (e.g., tenant_id, region)
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> bool:
    """Evaluate if a feature flag is enabled for the given context."""
    context = {"user_id": user_id, "group_id": group_id}
    # Remove None values from context
    context = {k: v for k, v in context.items() if v is not None}

    try:
        is_enabled = FeatureFlagsService.is_feature_enabled(
            db, redis_client, flag_key=flag_key, context=context
        )
    except ValueError as e:
        logger.warning(f"Could not evaluate feature flag '{flag_key}': {e}")
        # Return default state (usually False) or raise specific error?
        # For now, assume flag doesn't exist or error means disabled.
        # Consider raising 404 if flag not found is the specific error.
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found"
            )
        # For other errors (e.g., Redis down), a 500 might be appropriate
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error evaluating feature flag",
        )
    return is_enabled
