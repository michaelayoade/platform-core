from sqlalchemy import Column, String, Text, JSON
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

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
    metadata = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars


# Pydantic models for API
class AuditLogCreate(BaseModel):
    """
    Schema for creating an audit log entry.
    """
    actor_id: str
    event_type: str
    resource_type: str
    resource_id: str
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
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
    metadata: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True
