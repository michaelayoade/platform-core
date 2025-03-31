from datetime import datetime
from typing import List, Dict, Any
import sqlalchemy as sa
from redis import Redis

from app.core.settings import get_settings
from app.modules.health.models import ServiceStatus, ComponentStatus

settings = get_settings()


class HealthService:
    """
    Service for health and readiness checks.
    """
    
    @staticmethod
    def get_version() -> str:
        """
        Get the application version.
        """
        return settings.VERSION
    
    @staticmethod
    def get_timestamp() -> str:
        """
        Get the current timestamp in ISO format.
        """
        return datetime.utcnow().isoformat()
    
    @staticmethod
    async def check_database(engine) -> ComponentStatus:
        """
        Check database connectivity.
        """
        try:
            # Execute a simple query to check connectivity
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            
            return ComponentStatus(
                name="database",
                status=ServiceStatus.OK,
                details={"type": "postgresql"}
            )
        except Exception as e:
            return ComponentStatus(
                name="database",
                status=ServiceStatus.ERROR,
                error=str(e)
            )
    
    @staticmethod
    async def check_redis(redis_client: Redis) -> ComponentStatus:
        """
        Check Redis connectivity.
        """
        try:
            # Execute a simple PING command
            redis_client.ping()
            
            return ComponentStatus(
                name="redis",
                status=ServiceStatus.OK,
                details={"type": "redis"}
            )
        except Exception as e:
            return ComponentStatus(
                name="redis",
                status=ServiceStatus.ERROR,
                error=str(e)
            )
    
    @classmethod
    async def check_all_components(cls, engine, redis_client: Redis) -> List[ComponentStatus]:
        """
        Check all components.
        """
        db_status = await cls.check_database(engine)
        redis_status = await cls.check_redis(redis_client)
        
        return [db_status, redis_status]
    
    @classmethod
    def get_overall_status(cls, components: List[ComponentStatus]) -> ServiceStatus:
        """
        Determine overall status based on component statuses.
        """
        if any(component.status == ServiceStatus.ERROR for component in components):
            return ServiceStatus.ERROR
        
        if any(component.status == ServiceStatus.WARNING for component in components):
            return ServiceStatus.WARNING
        
        if all(component.status == ServiceStatus.OK for component in components):
            return ServiceStatus.OK
        
        return ServiceStatus.UNKNOWN
