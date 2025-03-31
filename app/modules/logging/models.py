"""
Models for the logging module.
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Index
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.db.base_model import Base


class LogEntry(Base):
    """
    Model for storing structured log entries in the database.
    """
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    level = Column(String(10), index=True)  # INFO, WARNING, ERROR, DEBUG, etc.
    service = Column(String(100), index=True)  # Service or component name
    message = Column(Text)
    context = Column(JSON, nullable=True)  # Additional context data
    trace_id = Column(String(100), nullable=True, index=True)  # For distributed tracing
    span_id = Column(String(100), nullable=True)  # For distributed tracing
    user_id = Column(String(100), nullable=True, index=True)  # User ID if applicable
    ip_address = Column(String(50), nullable=True)  # Client IP address if applicable
    
    # Create indexes for common query patterns
    __table_args__ = (
        Index('idx_logs_timestamp_level', timestamp, level),
        Index('idx_logs_service_level', service, level),
        Index('idx_logs_trace_id', trace_id),
    )


# Pydantic models for API
class LogEntryCreate(BaseModel):
    """
    Schema for creating a new log entry.
    """
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR, DEBUG, etc.)")
    service: str = Field(..., description="Service or component name")
    message: str = Field(..., description="Log message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    trace_id: Optional[str] = Field(None, description="Trace ID for distributed tracing")
    span_id: Optional[str] = Field(None, description="Span ID for distributed tracing")
    user_id: Optional[str] = Field(None, description="User ID if applicable")
    ip_address: Optional[str] = Field(None, description="Client IP address if applicable")


class LogEntryResponse(BaseModel):
    """
    Schema for log entry response.
    """
    id: int
    timestamp: datetime
    level: str
    service: str
    message: str
    context: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None

    class Config:
        orm_mode = True


class LogQueryParams(BaseModel):
    """
    Schema for log query parameters.
    """
    level: Optional[str] = None
    service: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    limit: int = 100
    offset: int = 0
