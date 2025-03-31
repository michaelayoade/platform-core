from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, String, Text

from app.db.base_model import BaseModel as DBBaseModel
from app.db.session import Base


class FeatureFlag(Base, DBBaseModel):
    """
    Feature flag model.
    """

    key = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=False, nullable=False)
    rules = Column(JSON, nullable=True)  # For user/group targeting


# Pydantic models for API
class FeatureFlagCreate(BaseModel):
    """
    Schema for creating a feature flag.
    """

    key: str
    name: str
    description: Optional[str] = None
    enabled: bool = False
    rules: Optional[List[Dict[str, Any]]] = Field(
        None, description="JSON array of rules for targeting (e.g., user IDs, groups)"
    )


class FeatureFlagUpdate(BaseModel):
    """
    Schema for updating a feature flag.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    rules: Optional[List[Dict[str, Any]]] = Field(
        None, description="JSON array of rules for targeting (e.g., user IDs, groups)"
    )


class FeatureFlagResponse(BaseModel):
    """
    Schema for feature flag response.
    """

    id: int
    key: str
    name: str
    description: Optional[str] = None
    enabled: bool
    rules: Optional[List[Dict[str, Any]]] = Field(
        None, description="JSON array of rules for targeting (e.g., user IDs, groups)"
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class FeatureFlagCheck(BaseModel):
    """
    Schema for checking if a feature flag is enabled for a user.
    """

    user_id: Optional[str] = None
    groups: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None


class FeatureFlagCheckResponse(BaseModel):
    """
    Schema for feature flag check response.
    """

    key: str
    enabled: bool
