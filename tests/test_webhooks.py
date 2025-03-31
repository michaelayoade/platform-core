"""
Tests for the webhooks module.
"""
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.webhooks.models import (
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEndpoint,
    WebhookEndpointCreate,
    WebhookSubscription,
    WebhookSubscriptionCreate,
)
from app.modules.webhooks.service import WebhooksService


def test_create_endpoint(client, db_session):
    """Test creating a webhook endpoint."""
    # Create endpoint data
    endpoint_data = {
        "url": "https://example.com/webhook",
        "description": "Test webhook endpoint",
        "secret": "test_secret",
        "active": True,
    }

    # Send request
    response = client.post("/webhooks/endpoints", json=endpoint_data)

    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == endpoint_data["url"]
    assert data["description"] == endpoint_data["description"]
    assert data["active"] == endpoint_data["active"]
    assert "secret" not in data  # Secret should not be returned

    # Check database
    db_endpoint = (
        db_session.query(WebhookEndpoint)
        .filter(WebhookEndpoint.id == data["id"])
        .first()
    )
    assert db_endpoint is not None
    assert db_endpoint.url == endpoint_data["url"]
    assert db_endpoint.secret == endpoint_data["secret"]  # Secret should be stored


def test_get_endpoints(client, db_session):
    """Test getting webhook endpoints."""
    # Create test endpoints
    for i in range(3):
        endpoint = WebhookEndpoint(
            url=f"https://example.com/webhook{i}",
            description=f"Test endpoint {i}",
            secret=f"secret{i}",
            active=True,
        )
        db_session.add(endpoint)
    db_session.commit()

    # Send request
    response = client.get("/webhooks/endpoints")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("secret" not in endpoint for endpoint in data)


def test_create_subscription(client, db_session):
    """Test creating a webhook subscription."""
    # Create test endpoint
    endpoint = WebhookEndpoint(
        url="https://example.com/webhook",
        description="Test endpoint",
        secret="secret",
        active=True,
    )
    db_session.add(endpoint)
    db_session.commit()

    # Create subscription data
    subscription_data = {
        "endpoint_id": endpoint.id,
        "event_types": ["user.created", "user.updated"],
        "description": "User events subscription",
    }

    # Send request
    response = client.post("/webhooks/subscriptions", json=subscription_data)

    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["endpoint_id"] == subscription_data["endpoint_id"]
    assert data["event_types"] == subscription_data["event_types"]
    assert data["description"] == subscription_data["description"]

    # Check database
    db_subscription = (
        db_session.query(WebhookSubscription)
        .filter(WebhookSubscription.id == data["id"])
        .first()
    )
    assert db_subscription is not None
    assert db_subscription.endpoint_id == subscription_data["endpoint_id"]
    assert db_subscription.event_types == subscription_data["event_types"]


def test_get_subscriptions(client, db_session):
    """Test getting webhook subscriptions."""
    # Create test endpoint
    endpoint = WebhookEndpoint(
        url="https://example.com/webhook",
        description="Test endpoint",
        secret="secret",
        active=True,
    )
    db_session.add(endpoint)
    db_session.commit()

    # Create test subscriptions
    for i in range(3):
        subscription = WebhookSubscription(
            endpoint_id=endpoint.id,
            event_types=[f"event.{i}"],
            description=f"Test subscription {i}",
        )
        db_session.add(subscription)
    db_session.commit()

    # Send request
    response = client.get("/webhooks/subscriptions")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@patch("httpx.AsyncClient.post")
def test_trigger_webhook(mock_post, client, db_session):
    """Test triggering a webhook."""
    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"
    mock_post.return_value = mock_response

    # Create test endpoint
    endpoint = WebhookEndpoint(
        url="https://example.com/webhook",
        description="Test endpoint",
        secret="test_secret",
        active=True,
    )
    db_session.add(endpoint)
    db_session.commit()

    # Create test subscription
    subscription = WebhookSubscription(
        endpoint_id=endpoint.id,
        event_types=["user.created"],
        description="User events subscription",
    )
    db_session.add(subscription)
    db_session.commit()

    # Create webhook trigger data
    trigger_data = {
        "event_type": "user.created",
        "payload": {"user_id": "user123", "email": "user@example.com"},
    }

    # Send request
    response = client.post("/webhooks/trigger", json=trigger_data)

    # Check response
    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Webhook delivery queued"
    assert data["event_type"] == trigger_data["event_type"]
    assert data["delivery_count"] == 1

    # Verify the HTTP request was made with correct data
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args

    # Check URL
    assert kwargs["url"] == endpoint.url

    # Check payload
    payload = json.loads(kwargs["content"])
    assert payload["event_type"] == trigger_data["event_type"]
    assert payload["payload"] == trigger_data["payload"]

    # Check signature
    headers = kwargs["headers"]
    assert "X-Webhook-Signature" in headers

    # Verify signature
    signature = headers["X-Webhook-Signature"]
    expected_signature = hmac.new(
        endpoint.secret.encode(), kwargs["content"], hashlib.sha256
    ).hexdigest()
    assert signature == expected_signature

    # Check database
    db_delivery = db_session.query(WebhookDelivery).first()
    assert db_delivery is not None
    assert db_delivery.endpoint_id == endpoint.id
    assert db_delivery.event_type == trigger_data["event_type"]
    assert db_delivery.status == WebhookDeliveryStatus.SUCCESS.value


@patch("httpx.AsyncClient.post")
def test_retry_failed_deliveries(mock_post, client, db_session):
    """Test retrying failed webhook deliveries."""
    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"
    mock_post.return_value = mock_response

    # Create test endpoint
    endpoint = WebhookEndpoint(
        url="https://example.com/webhook",
        description="Test endpoint",
        secret="test_secret",
        active=True,
    )
    db_session.add(endpoint)
    db_session.commit()

    # Create failed delivery
    delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        event_type="user.created",
        payload={"user_id": "user123"},
        status=WebhookDeliveryStatus.FAILED.value,
        attempt_count=1,
        last_response="Connection error",
        last_attempt_at=None,
    )
    db_session.add(delivery)
    db_session.commit()

    # Call the service method directly
    with patch.object(WebhooksService, "deliver_webhook") as mock_deliver:
        mock_deliver.return_value = True
        count = WebhooksService.retry_failed_deliveries(db_session)

        # Check result
        assert count == 1
        mock_deliver.assert_called_once()

        # Check database
        db_session.refresh(delivery)
        assert delivery.attempt_count == 2
