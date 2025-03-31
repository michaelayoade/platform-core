"""
Test configuration for the Platform Core service.
"""

# import os # Removed os import
# import sys # Removed sys import
# from typing import AsyncGenerator, Generator # Removed typing imports
# Remove unused MagicMock import

import fakeredis.aioredis  # Import fakeredis
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_model import BaseModel
from app.db.redis import get_redis
from app.db.session import Base, get_db
from app.main import app

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Create a fresh database for each test.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
    BaseModel.metadata.create_all(bind=engine)

    # Create session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

    # Drop tables
    Base.metadata.drop_all(bind=engine)
    BaseModel.metadata.drop_all(bind=engine)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """
    Create a test client for the FastAPI application.
    """

    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override the get_redis dependency
    def override_get_redis():
        """Override Redis dependency to use fakeredis for tests."""
        # Use FakeRedis for async tests
        fake_redis_instance = fakeredis.aioredis.FakeRedis()
        return fake_redis_instance

    # Apply overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    # Create client
    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides = {}
