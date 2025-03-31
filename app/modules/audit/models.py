from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, String, Text

from app.db.base_model import BaseModel as DBBaseModel
from app.db.session import Base


class AuditLog(Base, DBBaseModel):
    """
    Audit log model for tracking sensitive actions.
    """

    actor_id = Column(String(255), index=True, nullable=False)
    event_type = Column(String(100), index=True, nullable=False)
    resource_type = Column(String(100), index=True, nullable=False)
    resource_id = Column(String(255), index=True, nullable=False)
    action = Column(String(50), index=True, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    event_metadata = Column(
        JSON, nullable=True
    )  # Renamed from metadata to avoid SQLAlchemy conflict
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars


# Pydantic models for API
class AuditLogCreate(BaseModel):
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
        description="Type of the resource affected (e.g., 'user', 'config')",
    )
    resource_id: str
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None  # Renamed from metadata
    ip_address: Optional[str] = None


class AuditLogResponse(BaseModel):
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
    event_metadata: Optional[Dict[str, Any]] = None  # Renamed from metadata
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
