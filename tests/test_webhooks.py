"""
Tests for the webhooks module.
"""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.modules.webhooks.models import (
    WebhookDelivery,
    WebhookEndpoint,
    WebhookEventType,
    WebhookStatus,
    WebhookSubscription,
)
from app.modules.webhooks.service import WebhooksService


def test_create_endpoint(client, db_session):
    """Test creating a webhook endpoint."""
    # Create endpoint data
    endpoint_data = {
        "name": "Test Endpoint",
        "url": "https://example.com/webhook",
        "description": "Test webhook endpoint",
        "secret": "test_secret",
    }

    # Send request
    response = client.post("/api/v1/webhooks/endpoints/", json=endpoint_data)

    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == endpoint_data["name"]
    assert data["url"] == endpoint_data["url"]
    assert data["description"] == endpoint_data["description"]
    assert data["status"] == WebhookStatus.ACTIVE.value

    # Check database
    db_endpoint = db_session.query(WebhookEndpoint).filter(WebhookEndpoint.id == data["id"]).first()
    assert db_endpoint is not None
    assert db_endpoint.name == endpoint_data["name"]
    assert db_endpoint.url == endpoint_data["url"]
    assert db_endpoint.secret == endpoint_data["secret"]
    assert db_endpoint.status == WebhookStatus.ACTIVE.value


def test_get_endpoints(client, db_session):
    """Test getting webhook endpoints."""
    # Create test endpoints
    for i in range(3):
        endpoint = WebhookEndpoint(
            name=f"Test Endpoint {i}",
            url=f"https://example.com/webhook{i}",
            description=f"Test endpoint {i}",
            secret=f"secret{i}",
            status="active",
        )
        db_session.add(endpoint)
    db_session.commit()

    # Send request
    response = client.get("/api/v1/webhooks/endpoints/")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Ensure secret is not returned in the list view
    assert all(endpoint.get("secret") is None for endpoint in data)


def test_create_subscription(client, db_session):
    """Test creating a webhook subscription."""
    # Create test endpoint
    endpoint = WebhookEndpoint(
        name="Subscription Test Endpoint",
        url="https://example.com/webhook",
        description="Test endpoint",
        secret="secret",
        status="active",
    )
    db_session.add(endpoint)
    db_session.commit()

    # Create subscription data conforming to WebhookSubscriptionCreate model
    subscription_data = {
        "event_type": WebhookEventType.AUDIT_EVENT.value,  # Use enum value
        # "filter_conditions": {} # Optional field
    }

    # Send request
    response = client.post(f"/api/v1/webhooks/endpoints/{endpoint.id}/subscriptions/", json=subscription_data)

    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["endpoint_id"] == endpoint.id
    assert data["event_type"] == subscription_data["event_type"]

    # Check database
    db_subscription = db_session.query(WebhookSubscription).filter(WebhookSubscription.id == data["id"]).first()
    assert db_subscription is not None
    assert db_subscription.endpoint_id == endpoint.id
    assert db_subscription.event_type == subscription_data["event_type"]


def test_get_subscriptions(client, db_session):
    """Test getting webhook subscriptions."""
    # Create test endpoint
    endpoint = WebhookEndpoint(
        name="Get Subscriptions Test",
        url="https://example.com/webhook",
        description="Test endpoint",
        secret="secret",
        status="active",
    )
    db_session.add(endpoint)
    db_session.commit()

    # Create multiple subscriptions for the endpoint
    event_types = ["config.created", "feature_flag.updated"]
    for et in event_types:
        subscription = WebhookSubscription(
            endpoint_id=endpoint.id,
            event_type=et,  # Use the single event_type field
        )
        db_session.add(subscription)
    db_session.commit()

    # Send request to get subscriptions for the endpoint
    response = client.get(f"/api/v1/webhooks/endpoints/{endpoint.id}/subscriptions")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(event_types)  # Check if we got all created subscriptions
    assert {sub["event_type"] for sub in data} == {et for et in event_types}


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
        name="Trigger Test Endpoint",
        url="https://example.com/webhook",
        description="Test endpoint",
        secret="test_secret",
        status="active",
    )
    db_session.add(endpoint)
    db_session.commit()

    # Create subscription for the relevant event type
    subscription = WebhookSubscription(
        endpoint_id=endpoint.id,
        event_type="config.created",  # Subscribe to the specific VALID event
    )
    db_session.add(subscription)
    db_session.commit()

    # Create webhook trigger data (payload only)
    event_type = "config.created"  # Use VALID event type
    payload = {"config_key": "new_setting", "value": "enabled"}

    # Send request to the correct path with event_type in URL
    response = client.post(f"/api/v1/webhooks/trigger/{event_type}", json=payload)

    # Check response
    assert response.status_code == 202
    data = response.json()
    assert data["event_type"] == event_type
    assert data["delivery_count"] == 1  # Expecting 1 delivery based on test setup
    assert isinstance(data["delivery_ids"], list)
    assert len(data["delivery_ids"]) == 1

    # Verify the HTTP request was made with correct data
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args

    # Check URL - Should be the first positional argument
    assert args[0] == endpoint.url

    # Check payload - Service passes 'json' keyword argument
    payload_data = kwargs["json"]
    assert payload_data == payload  # Check the actual payload content

    # Check signature
    headers = kwargs["headers"]
    assert "X-Webhook-Signature" in headers

    # Verify signature
    signature = headers["X-Webhook-Signature"]
    expected_signature = hmac.new(
        endpoint.secret.encode(), json.dumps(payload_data).encode(), hashlib.sha256
    ).hexdigest()
    assert signature == expected_signature

    # Check database
    db_delivery = db_session.query(WebhookDelivery).first()
    assert db_delivery is not None
    assert db_delivery.endpoint_id == endpoint.id
    assert db_delivery.event_type == event_type
    assert db_delivery.success


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
        name="Retry Test Endpoint",
        url="https://example.com/webhook",
        description="Test endpoint",
        secret="test_secret",
        status="active",
    )
    db_session.add(endpoint)
    db_session.commit()

    # Create a failed delivery
    failed_delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        event_type=WebhookEventType.CONFIG_UPDATED.value,
        payload={"key": "value"},
        success=False,
        response_status=500,
        attempt_count=1,
        next_retry_at=datetime.utcnow() - timedelta(minutes=1),
    )
    db_session.add(failed_delivery)
    db_session.commit()

    # Mock the delivery function to avoid actual HTTP calls
    with patch(
        "app.modules.webhooks.service.WebhooksService._deliver_webhook", return_value=(True, 200, "OK")
    ) as mock_delivery:
        # Call the retry function - need to run it in an event loop since it's async
        loop = asyncio.get_event_loop()
        loop.run_until_complete(WebhooksService.retry_failed_deliveries(db=db_session, test_mode=True))

        # Assertions
        mock_delivery.assert_called_once()

    # OR call an API endpoint if one exists
    # client.post("/api/v1/webhooks/deliveries/retry")
