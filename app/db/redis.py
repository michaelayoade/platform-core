from functools import lru_cache

import redis

from app.core.settings import get_settings

settings = get_settings()


@lru_cache()
def get_redis_client():
    """
    Get a Redis client instance.
    """
    return redis.from_url(str(settings.REDIS_URL), decode_responses=True)


# For use as a FastAPI dependency
def get_redis():
    """
    Get a Redis client as a dependency.
    """
    client = get_redis_client()
    try:
        yield client
    finally:
        # Redis connections are returned to the connection pool automatically
        pass
