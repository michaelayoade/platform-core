from datetime import datetime
from typing import Any, Dict, Optional

# Alias Pydantic's BaseModel to avoid conflict
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field
from sqlalchemy import JSON, String, Text

# Corrected import for the base model
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_model import BaseModel


class AuditLog(BaseModel):
    """
    Audit log model for tracking sensitive actions.
    Inherits id, created_at, updated_at from BaseModel.
    """

    # Explicitly define tablename (though BaseModel should handle it)
    __tablename__ = "auditlog"

    actor_id: Mapped[str] = mapped_column(String(255), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_id: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 can be up to 45 chars


# Pydantic models for API
class AuditLogCreate(PydanticBaseModel):
    """
    Schema for creating an audit log entry.
    """

    actor_id: str
    event_type: str = Field(
        ...,
        max_length=50,
        description="Type of the event (e.g., 'user_login', 'config_update')",
    )
    resource_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type of the resource being acted upon (e.g., 'user', 'config')",
    )
    resource_id: Optional[str] = Field(
        None,
        max_length=255,
        description="Identifier of the specific resource being acted upon",
    )
    action: str = Field(..., max_length=50, description="Action performed (e.g., 'create', 'update')")
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional contextual information as JSON")
    ip_address: Optional[str] = None


class AuditLogResponse(PydanticBaseModel):
    """
    Schema for audit log response.
    """

    id: int
    actor_id: str
    event_type: str
    resource_type: str
    resource_id: str
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
