import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Create the SQLAlchemy engine
try:
    engine = create_async_engine(
        str(settings.DB.DATABASE_URL),
        pool_pre_ping=True,
        echo=settings.DB.DB_ECHO,
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False, default=str),
    )
except Exception as e:
    logging.error(
        f"Failed to create database engine: {e}" f"URL: {settings.DB.DATABASE_URL.render_as_string(hide_password=True)}"
    )
    raise

# Create a configured "Session" class
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Create Base class for models
Base = declarative_base()

# Import all models here to ensure they are registered with Base.metadata
from app.modules.audit.models import AuditLog  # noqa
from app.modules.config.models import ConfigItem  # noqa
from app.modules.feature_flags.models import FeatureFlag  # noqa
from app.modules.logging.models import LogEntry  # noqa
from app.modules.notifications.models import Notification  # noqa

# Import webhook models individually to avoid unused import warnings
from app.modules.webhooks.models import WebhookDelivery  # noqa
from app.modules.webhooks.models import WebhookEndpoint  # noqa
from app.modules.webhooks.models import WebhookSubscription  # noqa


# Dependency to get DB session (async)
async def get_db() -> AsyncSession:
    """
    Dependency that provides an asynchronous database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Optional: commit here if you want auto-commit, but usually handled in endpoint/service
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        # finally:
        # session is automatically closed by async context manager
