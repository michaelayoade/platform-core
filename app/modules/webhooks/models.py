"""
Models for the webhooks module.
"""

import enum
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db.base_model import Base


class WebhookEventType(str, enum.Enum):
    """
    Enum for webhook event types.
    """

    CONFIG_CREATED = "config.created"
    CONFIG_UPDATED = "config.updated"
    CONFIG_DELETED = "config.deleted"
    FEATURE_FLAG_CREATED = "feature_flag.created"
    FEATURE_FLAG_UPDATED = "feature_flag.updated"
    FEATURE_FLAG_DELETED = "feature_flag.deleted"
    AUDIT_EVENT = "audit.event"
    SYSTEM_ALERT = "system.alert"


class WebhookStatus(str, enum.Enum):
    """
    Enum for webhook status.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"  # Too many failures


class WebhookEndpoint(Base):
    """
    Model for storing webhook endpoints.
    """

    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    secret = Column(String(100), nullable=True)  # For HMAC signature verification
    status = Column(String(20), default=WebhookStatus.ACTIVE.value)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    headers = Column(JSON, nullable=True)  # Custom headers to include in requests
    retry_count = Column(Integer, default=3)  # Number of retries for failed webhooks
    timeout_seconds = Column(Integer, default=5)  # Timeout for webhook requests

    # Create indexes for common query patterns
    __table_args__ = (Index("idx_webhook_endpoints_status", status),)


class WebhookSubscription(Base):
    """
    Model for storing webhook subscriptions to event types.
    """

    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(
        Integer, ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(String(50), nullable=False)
    filter_conditions = Column(
        JSON, nullable=True
    )  # Optional conditions for triggering
    created_at = Column(DateTime, default=func.now())

    # Create indexes for common query patterns
    __table_args__ = (
        Index("idx_webhook_subscriptions_endpoint_event", endpoint_id, event_type),
    )


class WebhookDelivery(Base):
    """
    Model for storing webhook delivery attempts.
    """

    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(
        Integer, ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    request_headers = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, default=False)
    attempt_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    # Create indexes for common query patterns
    __table_args__ = (
        Index("idx_webhook_deliveries_success", success),
        Index("idx_webhook_deliveries_next_retry", next_retry_at),
    )


# Pydantic models for API
class WebhookEndpointCreate(BaseModel):
    """
    Schema for creating a new webhook endpoint.
    """

    name: str = Field(..., description="Name of the webhook endpoint")
    url: HttpUrl = Field(..., description="URL of the webhook endpoint")
    description: Optional[str] = Field(
        None, description="Description of the webhook endpoint"
    )
    secret: Optional[str] = Field(
        None, description="Secret for HMAC signature verification"
    )
    headers: Optional[Dict[str, str]] = Field(
        None, description="Custom headers to include in requests"
    )
    retry_count: Optional[int] = Field(
        3, description="Number of retries for failed webhooks"
    )
    timeout_seconds: Optional[int] = Field(
        5, description="Timeout for webhook requests in seconds"
    )


class WebhookEndpointUpdate(BaseModel):
    """
    Schema for updating a webhook endpoint.
    """

    name: Optional[str] = Field(None, description="Name of the webhook endpoint")
    url: Optional[HttpUrl] = Field(None, description="URL of the webhook endpoint")
    description: Optional[str] = Field(
        None, description="Description of the webhook endpoint"
    )
    secret: Optional[str] = Field(
        None, description="Secret for HMAC signature verification"
    )
    status: Optional[WebhookStatus] = Field(
        None, description="Status of the webhook endpoint"
    )
    headers: Optional[Dict[str, str]] = Field(
        None, description="Custom headers to include in requests"
    )
    retry_count: Optional[int] = Field(
        None, description="Number of retries for failed webhooks"
    )
    timeout_seconds: Optional[int] = Field(
        None, description="Timeout for webhook requests in seconds"
    )


class WebhookSubscriptionCreate(BaseModel):
    """
    Schema for creating a new webhook subscription.
    """

    event_type: WebhookEventType = Field(..., description="Event type to subscribe to")
    filter_conditions: Optional[Dict[str, Any]] = Field(
        None, description="Optional conditions for triggering"
    )


class WebhookEndpointResponse(BaseModel):
    """
    Schema for webhook endpoint response.
    """

    id: int
    name: str
    url: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    retry_count: int
    timeout_seconds: int

    class Config:
        orm_mode = True


class WebhookSubscriptionResponse(BaseModel):
    """
    Schema for webhook subscription response.
    """

    id: int
    endpoint_id: int
    event_type: str
    filter_conditions: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        orm_mode = True


class WebhookDeliveryResponse(BaseModel):
    """
    Schema for webhook delivery response.
    """

    id: int
    endpoint_id: int
    event_type: str
    payload: Dict[str, Any]
    response_status: Optional[int] = None
    success: bool
    attempt_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class WebhookTestRequest(BaseModel):
    """
    Schema for testing a webhook endpoint.
    """

    event_type: WebhookEventType = Field(..., description="Event type to test")
    payload: Dict[str, Any] = Field(..., description="Test payload to send")
