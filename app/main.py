import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

# Import settings and DB initialization
from app.core.settings import get_settings

# Import routers for different modules
from app.modules.audit.router import router as audit_router
from app.modules.config.router import router as config_router
from app.modules.feature_flags.router import router as feature_flags_router
from app.modules.health.router import router as health_router
from app.modules.logging.router import router as logging_router
from app.modules.notifications.router import router as notifications_router
from app.modules.webhooks.router import router as webhooks_router
from app.utils.redis_client import RedisClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

settings = get_settings()

# Define OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Health",
        "description": "Health check endpoints for monitoring application status and readiness.",
    },
    {
        "name": "Config",
        "description": "Configuration management endpoints for storing and retrieving application settings.",
    },
    {
        "name": "Audit",
        "description": "Audit logging endpoints for tracking sensitive actions for compliance and security.",
    },
    {
        "name": "Feature Flags",
        "description": "Feature flag endpoints for toggling features on/off globally or for specific users/groups.",
    },
    {
        "name": "Logging",
        "description": "Structured logging endpoints for storing and retrieving application logs.",
    },
    {
        "name": "Webhooks",
        "description": "Webhook endpoints for registering webhook endpoints and triggering webhooks for events.",
    },
    {
        "name": "Notifications",
        "description": "Notification endpoints for creating and managing user notifications.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events."""
    # Startup
    logger.info("Starting up Platform Core service...")
    # Initialize Redis connection
    await RedisClient.initialize()
    logger.info("Redis client initialized.")
    # Database initialization (optional, often handled by Alembic)
    # logger.info("Database initialized.")
    yield
    # Shutdown
    logger.info("Shutting down Platform Core service...")
    # Close Redis connection
    await RedisClient.close()
    logger.info("Redis client closed.")
    logger.info("Platform Core service finished shutting down.")


app = FastAPI(
    title="Dotmac Platform Core",
    description="""
    Centralized service for configuration, logging, auditing, webhooks, notifications, feature flags, and health checks.
    ## Features
    * **Configuration Management**: Store and retrieve configuration values with namespacing,
      versioning, and access control
    * **Structured Logging**: Store and retrieve structured application logs
    * **Audit Logging**: Track sensitive actions for compliance and security
    * **Webhooks**: Register webhook endpoints and trigger webhooks for events
    * **Notifications**: Create and manage user notifications
    * **Feature Flags**: Toggle features on/off globally or for specific users/groups
    * **Health Checks**: Monitor the health and readiness of your application
    ## Authentication
    This API uses JWT tokens for authentication. The token should be provided in the
    Authorization header as a Bearer token.
    """,
    version=settings.VERSION,
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Support",
        "email": "support@dotmac.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

# Add CORS middleware if needed
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Setup Prometheus instrumentation
Instrumentator().instrument(app).expose(app)


@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint providing a simple welcome message.

    Returns:
        dict: A welcome message
    """
    return {
        "message": "Welcome to the Dotmac Platform Core API",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }


# Include routers
app.include_router(health_router, prefix="/health", tags=["Health"])

app.include_router(audit_router, prefix=f"{settings.API_V1_STR}/audit", tags=["Audit Logs"])
app.include_router(config_router, prefix=f"{settings.API_V1_STR}/config", tags=["Configuration"])
app.include_router(
    feature_flags_router,
    prefix=f"{settings.API_V1_STR}/feature-flags",
    tags=["Feature Flags"],
)
app.include_router(logging_router, prefix=f"{settings.API_V1_STR}/logs", tags=["Logging"])
app.include_router(
    notifications_router,
    prefix=f"{settings.API_V1_STR}/notifications",
    tags=["Notifications"],
)
app.include_router(webhooks_router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["Webhooks"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


if __name__ == "__main__":
    import uvicorn

    # Configuration for Uvicorn can be loaded from environment variables
    # or a config file for production deployments.
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "False").lower() == "true"

    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
