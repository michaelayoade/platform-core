from fastapi import APIRouter, Depends
from redis import Redis

from app.core.settings import get_settings
from app.db.redis import get_redis
from app.db.session import engine
from app.modules.health.models import HealthCheck, ReadinessCheck, ServiceStatus
from app.modules.health.service import HealthService

settings = get_settings()
router = APIRouter()


@router.get("/healthz", response_model=HealthCheck)
async def health_check():
    """
    Basic liveness probe.
    """
    return HealthCheck(
        status=ServiceStatus.OK,
        version=HealthService.get_version(),
        timestamp=HealthService.get_timestamp(),
    )


@router.get("/readyz", response_model=ReadinessCheck)
async def readiness_check(redis_client: Redis = Depends(get_redis)):
    """
    Readiness probe checking all dependencies.
    """
    components = await HealthService.check_all_components(engine, redis_client)
    overall_status = HealthService.get_overall_status(components)

    return ReadinessCheck(
        status=overall_status,
        version=HealthService.get_version(),
        timestamp=HealthService.get_timestamp(),
        components=components,
    )


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Note: In a production setup, this would be implemented using
    prometheus-fastapi-instrumentator or a similar library.
    """
    return {"message": "Metrics endpoint - to be implemented with Prometheus"}
