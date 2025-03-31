"""
Models for the notifications module.
"""
import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base_model import Base


class NotificationType(str, enum.Enum):
    """
    Enum for notification types.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    SYSTEM = "system"


class NotificationPriority(str, enum.Enum):
    """
    Enum for notification priorities.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, enum.Enum):
    """
    Enum for notification status.
    """

    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Notification(Base):
    """
    Model for storing notifications.
    """

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(
        String(20), nullable=False, default=NotificationType.INFO.value
    )
    priority = Column(
        String(20), nullable=False, default=NotificationPriority.MEDIUM.value
    )
    status = Column(
        String(20), nullable=False, default=NotificationStatus.PENDING.value
    )
    recipient_id = Column(
        String(100), nullable=False, index=True
    )  # User ID or group ID
    recipient_type = Column(String(20), nullable=False)  # "user" or "group"
    sender_id = Column(String(100), nullable=True)  # User ID or system ID
    created_at = Column(DateTime, default=func.now(), index=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration time
    data = Column(JSON, nullable=True)  # Additional data for the notification
    action_url = Column(String(500), nullable=True)  # Optional URL for action button

    # Create indexes for common query patterns
    __table_args__ = (
        Index("idx_notifications_recipient_status", recipient_id, status),
        Index("idx_notifications_created_at", created_at),
    )


# Pydantic models for API
class NotificationCreate(BaseModel):
    """
    Schema for creating a new notification.
    """

    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    notification_type: NotificationType = Field(
        NotificationType.INFO, description="Type of notification"
    )
    priority: NotificationPriority = Field(
        NotificationPriority.MEDIUM, description="Priority of notification"
    )
    recipient_id: str = Field(..., description="ID of the recipient (user or group)")
    recipient_type: str = Field(
        ..., description="Type of recipient ('user' or 'group')"
    )
    sender_id: Optional[str] = Field(
        None, description="ID of the sender (user or system)"
    )
    expires_at: Optional[datetime] = Field(None, description="Optional expiration time")
    data: Optional[Dict[str, Any]] = Field(
        None, description="Additional data for the notification"
    )
    action_url: Optional[str] = Field(
        None, description="Optional URL for action button"
    )


class NotificationUpdate(BaseModel):
    """
    Schema for updating a notification.
    """

    status: Optional[NotificationStatus] = Field(
        None, description="Status of the notification"
    )
    read_at: Optional[datetime] = Field(
        None, description="Time when the notification was read"
    )


class NotificationResponse(BaseModel):
    """
    Schema for notification response.
    """

    id: int
    title: str
    message: str
    notification_type: str
    priority: str
    status: str
    recipient_id: str
    recipient_type: str
    sender_id: Optional[str] = None
    created_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = None

    class Config:
        orm_mode = True


class NotificationBulkCreate(BaseModel):
    """
    Schema for creating multiple notifications at once.
    """

    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    notification_type: NotificationType = Field(
        NotificationType.INFO, description="Type of notification"
    )
    priority: NotificationPriority = Field(
        NotificationPriority.MEDIUM, description="Priority of notification"
    )
    recipient_ids: List[str] = Field(..., description="List of recipient IDs")
    recipient_type: str = Field(
        ..., description="Type of recipients ('user' or 'group')"
    )
    sender_id: Optional[str] = Field(
        None, description="ID of the sender (user or system)"
    )
    expires_at: Optional[datetime] = Field(None, description="Optional expiration time")
    data: Optional[Dict[str, Any]] = Field(
        None, description="Additional data for the notification"
    )
    action_url: Optional[str] = Field(
        None, description="Optional URL for action button"
    )
