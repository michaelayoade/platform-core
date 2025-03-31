from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from enum import Enum


class ServiceStatus(str, Enum):
    """
    Enum for service status values.
    """
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class HealthCheck(BaseModel):
    """
    Health check response model.
    """
    status: ServiceStatus
    version: str
    timestamp: str


class ComponentStatus(BaseModel):
    """
    Status of an individual component.
    """
    name: str
    status: ServiceStatus
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ReadinessCheck(BaseModel):
    """
    Readiness check response model.
    """
    status: ServiceStatus
    version: str
    timestamp: str
    components: List[ComponentStatus]
