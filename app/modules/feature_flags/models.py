from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field
from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_model import BaseModel


class FeatureFlag(BaseModel):
    """
    Model for feature flags.
    Inherits id, created_at, updated_at from BaseModel.
    """

    __tablename__ = "featureflag"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rules: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)


# Pydantic models for API
class FeatureFlagBase(PydanticBaseModel):
    """
    Schema for feature flag base.
    """

    key: str = Field(..., max_length=100, description="Unique key for the feature flag")
    name: str = Field(..., description="Name of the feature flag")
    description: Optional[str] = Field(None, description="Description of the feature flag")


class FeatureFlagCreate(FeatureFlagBase):
    """
    Schema for creating a feature flag.
    """

    enabled: bool = False
    rules: Optional[List[Dict[str, Any]]] = Field(
        None, description="JSON array of rules for targeting (e.g., user IDs, groups)"
    )


class FeatureFlagUpdate(PydanticBaseModel):
    """
    Schema for updating a feature flag.
    """

    name: Optional[str] = Field(None, description="Name of the feature flag")
    description: Optional[str] = Field(None, description="Description of the feature flag")
    enabled: Optional[bool] = Field(None, description="Whether the feature flag is enabled")
    rules: Optional[List[Dict[str, Any]]] = Field(
        None, description="JSON array of rules for targeting (e.g., user IDs, groups)"
    )


class FeatureFlagResponse(FeatureFlagBase):
    """
    Schema for feature flag response.
    """

    id: int
    enabled: bool
    rules: Optional[List[Dict[str, Any]]] = Field(
        None, description="JSON array of rules for targeting (e.g., user IDs, groups)"
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeatureFlagCheck(PydanticBaseModel):
    """
    Schema for checking if a feature flag is enabled for a user.
    """

    user_id: Optional[str] = Field(None, description="User ID")
    groups: Optional[List[str]] = Field(None, description="List of groups")
    attributes: Optional[Dict[str, Any]] = Field(None, description="User attributes")


class FeatureFlagCheckResponse(PydanticBaseModel):
    """
    Schema for feature flag check response.
    """

    key: str
    enabled: bool
