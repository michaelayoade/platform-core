"""
Tests for the health module.
"""
from fastapi.testclient import TestClient
from app.modules.health.models import ServiceStatus


def test_health_check(client):
    """
    Test the health check endpoint.
    """
    response = client.get("/health/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ServiceStatus.OK
    assert "version" in data
    assert "timestamp" in data


def test_readiness_check(client):
    """
    Test the readiness check endpoint.
    
    Note: This test will pass because we're using mock dependencies.
    In a real environment, this would check actual database and Redis connectivity.
    """
    response = client.get("/health/readyz")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data
    assert "components" in data
    assert len(data["components"]) > 0


def test_metrics(client):
    """
    Test the metrics endpoint.
    """
    response = client.get("/health/metrics")
    assert response.status_code == 200
