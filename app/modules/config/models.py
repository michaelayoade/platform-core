from datetime import datetime
from typing import List, Optional

# Alias Pydantic BaseModel
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_model import BaseModel


class ConfigScope(BaseModel):
    """
    Configuration scope model (e.g., 'auth', 'billing').
    """

    # Use mapped_column for explicit column definitions
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship - Mapped[List[...]] is standard for one-to-many
    configs: Mapped[List["ConfigItem"]] = relationship(
        "ConfigItem", back_populates="scope", cascade="all, delete-orphan"
    )


class ConfigItem(BaseModel):
    """
    Configuration item model.
    """

    key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_secret: Mapped[bool] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0=false, 1=true

    # Foreign keys - use Mapped[int] for the type, keep ForeignKey in mapped_column
    scope_id: Mapped[int] = mapped_column(ForeignKey("configscope.id"), nullable=False)

    # Relationships
    scope: Mapped["ConfigScope"] = relationship("ConfigScope", back_populates="configs")
    history: Mapped[List["ConfigHistory"]] = relationship(
        "ConfigHistory", back_populates="config_item", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (UniqueConstraint("scope_id", "key", name="uix_config_scope_key"),)


class ConfigHistory(BaseModel):
    """
    Configuration history model for tracking changes.
    """

    value: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Foreign Key
    config_id: Mapped[int] = mapped_column(ForeignKey("configitem.id"), nullable=False)

    # Relationship
    config_item: Mapped["ConfigItem"] = relationship(
        "ConfigItem", back_populates="history"
    )


# Pydantic models for API


# Use aliased PydanticBaseModel
class ConfigScopeBase(PydanticBaseModel):
    name: str = Field(..., max_length=100, description="Scope name (e.g., 'auth')")
    description: Optional[str] = None


# Use aliased PydanticBaseModel
class ConfigScopeCreate(ConfigScopeBase):
    pass


# Use aliased PydanticBaseModel
class ConfigScopeUpdate(ConfigScopeBase):
    name: Optional[str] = None  # Allow partial updates


# Use aliased PydanticBaseModel
class ConfigScopeResponse(ConfigScopeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Use aliased PydanticBaseModel
class ConfigItemBase(PydanticBaseModel):
    key: str = Field(..., max_length=255, description="Configuration key")
    value: str = Field(..., description="Configuration value")
    description: Optional[str] = None
    is_secret: bool = False


# Use aliased PydanticBaseModel
class ConfigItemCreate(ConfigItemBase):
    scope_id: int


# Use aliased PydanticBaseModel
class ConfigItemUpdate(PydanticBaseModel):  # Separate base for update flexibility
    value: Optional[str] = None
    description: Optional[str] = None
    is_secret: Optional[bool] = None


# Use aliased PydanticBaseModel
class ConfigItemResponse(ConfigItemBase):
    id: int
    scope_id: int
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Use aliased PydanticBaseModel
class ConfigHistoryResponse(PydanticBaseModel):
    id: int
    config_id: int
    version: int
    key: str
    value: str
    description: Optional[str]
    is_secret: bool
    created_at: datetime

    class Config:
        orm_mode = True
