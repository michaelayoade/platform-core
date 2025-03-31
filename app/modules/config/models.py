from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_model import BaseModel as DBBaseModel
from app.db.session import Base


class ConfigScope(Base, DBBaseModel):
    """
    Configuration scope model (e.g., 'auth', 'billing').
    """

    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    configs = relationship(
        "ConfigItem", back_populates="scope", cascade="all, delete-orphan"
    )


class ConfigItem(Base, DBBaseModel):
    """
    Configuration item model.
    """

    key = Column(String(255), index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_secret = Column(Integer, default=0, nullable=False)  # 0=false, 1=true

    # Foreign keys
    scope_id = Column(Integer, ForeignKey("configscope.id"), nullable=False)

    # Relationships
    scope: ConfigScope = relationship("ConfigScope", back_populates="configs")
    history: List["ConfigHistory"] = relationship(
        "ConfigHistory", back_populates="config_item", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (UniqueConstraint("scope_id", "key", name="uix_config_scope_key"),)


class ConfigHistory(Base, DBBaseModel):
    """
    Configuration history model for tracking changes.
    """

    value = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    changed_by = Column(String(255), nullable=True)

    # Foreign keys
    config_id = Column(Integer, ForeignKey("configitem.id"), nullable=False)

    # Relationships
    config_item: "ConfigItem" = relationship("ConfigItem", back_populates="history")


# Pydantic models for API
class ConfigScopeCreate(BaseModel):
    """
    Schema for creating a config scope.
    """

    name: str
    description: Optional[str] = None


class ConfigScopeResponse(BaseModel):
    """
    Schema for config scope response.
    """

    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ConfigItemCreate(BaseModel):
    """
    Schema for creating a config item.
    """

    key: str = Field(..., max_length=255, description="Name/key of the config item")
    value: str
    description: Optional[str] = None
    is_secret: bool = False


class ConfigItemUpdate(BaseModel):
    """
    Schema for updating a config item.
    """

    value: str
    description: Optional[str] = None
    is_secret: Optional[bool] = None


class ConfigItemResponse(BaseModel):
    """
    Schema for config item response.
    """

    id: int
    key: str
    value: str
    description: Optional[str] = None
    version: int
    is_secret: bool
    scope_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ConfigHistoryResponse(BaseModel):
    """
    Schema for config history response.
    """

    id: int
    value: str
    version: int
    changed_by: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
