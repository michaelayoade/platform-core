from sqlalchemy import Column, String, Text, Boolean, JSON, UniqueConstraint
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

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
    rules: Optional[Dict[str, Any]] = None


class FeatureFlagUpdate(BaseModel):
    """
    Schema for updating a feature flag.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    rules: Optional[Dict[str, Any]] = None


class FeatureFlagResponse(BaseModel):
    """
    Schema for feature flag response.
    """
    id: int
    key: str
    name: str
    description: Optional[str] = None
    enabled: bool
    rules: Optional[Dict[str, Any]] = None
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
