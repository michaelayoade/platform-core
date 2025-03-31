"""
Tests for the notifications module.
"""

from datetime import datetime, timedelta

from app.modules.notifications.models import Notification, NotificationPriority, NotificationStatus, NotificationType


def test_create_notification(client, db_session):
    """Test creating a notification."""
    # Create notification data
    notification_data = {
        "title": "Test Notification",
        "message": "This is a test notification",
        "notification_type": "SYSTEM",
        "priority": "NORMAL",
        "recipient_id": "user123",
        "recipient_type": "user",
        "sender_id": "system",
        "data": {"key": "value"},
    }

    # Send request
    response = client.post("/notifications/", json=notification_data)

    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == notification_data["title"]
    assert data["message"] == notification_data["message"]
    assert data["notification_type"] == notification_data["notification_type"]
    assert data["priority"] == notification_data["priority"]
    assert data["recipient_id"] == notification_data["recipient_id"]
    assert data["status"] == "PENDING"

    # Check database
    db_notification = db_session.query(Notification).filter(Notification.id == data["id"]).first()
    assert db_notification is not None
    assert db_notification.title == notification_data["title"]


def test_get_notifications(client, db_session):
    """Test getting notifications."""
    # Create test notifications
    for i in range(3):
        notification = Notification(
            title=f"Test {i}",
            message=f"Test message {i}",
            notification_type=NotificationType.SYSTEM.value,
            priority=NotificationPriority.NORMAL.value,
            recipient_id="user123",
            recipient_type="user",
            sender_id="system",
        )
        db_session.add(notification)
    db_session.commit()

    # Send request
    response = client.get("/notifications/?recipient_id=user123")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["recipient_id"] == "user123"


def test_mark_as_read(client, db_session):
    """Test marking a notification as read."""
    # Create test notification
    notification = Notification(
        title="Test",
        message="Test message",
        notification_type=NotificationType.SYSTEM.value,
        priority=NotificationPriority.NORMAL.value,
        recipient_id="user123",
        recipient_type="user",
        sender_id="system",
    )
    db_session.add(notification)
    db_session.commit()

    # Send request
    response = client.post(f"/notifications/{notification.id}/read")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READ"
    assert data["read_at"] is not None

    # Check database
    db_notification = db_session.query(Notification).filter(Notification.id == notification.id).first()
    assert db_notification.status == NotificationStatus.READ.value
    assert db_notification.read_at is not None


def test_get_unread_count(client, db_session):
    """Test getting unread notification count."""
    # Create test notifications (2 unread, 1 read)
    for i in range(2):
        notification = Notification(
            title=f"Unread {i}",
            message=f"Unread message {i}",
            notification_type=NotificationType.SYSTEM.value,
            priority=NotificationPriority.NORMAL.value,
            recipient_id="user123",
            recipient_type="user",
            sender_id="system",
            status=NotificationStatus.PENDING.value,
        )
        db_session.add(notification)

    read_notification = Notification(
        title="Read",
        message="Read message",
        notification_type=NotificationType.SYSTEM.value,
        priority=NotificationPriority.NORMAL.value,
        recipient_id="user123",
        recipient_type="user",
        sender_id="system",
        status=NotificationStatus.READ.value,
        read_at=datetime.utcnow(),
    )
    db_session.add(read_notification)
    db_session.commit()

    # Send request
    response = client.get("/notifications/count?recipient_id=user123")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["unread_count"] == 2


def test_mark_all_as_read(client, db_session):
    """Test marking all notifications as read."""
    # Create test notifications
    for i in range(3):
        notification = Notification(
            title=f"Test {i}",
            message=f"Test message {i}",
            notification_type=NotificationType.SYSTEM.value,
            priority=NotificationPriority.NORMAL.value,
            recipient_id="user123",
            recipient_type="user",
            sender_id="system",
            status=NotificationStatus.PENDING.value,
        )
        db_session.add(notification)
    db_session.commit()

    # Send request
    response = client.post("/notifications/read-all?recipient_id=user123")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["marked_as_read"] == 3

    # Check database
    unread_count = (
        db_session.query(Notification)
        .filter(
            Notification.recipient_id == "user123",
            Notification.status != NotificationStatus.READ.value,
        )
        .count()
    )
    assert unread_count == 0


def test_clean_expired_notifications(client, db_session):
    """Test cleaning expired notifications."""
    # Create expired notification
    expired_notification = Notification(
        title="Expired",
        message="Expired message",
        notification_type=NotificationType.SYSTEM.value,
        priority=NotificationPriority.NORMAL.value,
        recipient_id="user123",
        recipient_type="user",
        sender_id="system",
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    db_session.add(expired_notification)

    # Create active notification
    active_notification = Notification(
        title="Active",
        message="Active message",
        notification_type=NotificationType.SYSTEM.value,
        priority=NotificationPriority.NORMAL.value,
        recipient_id="user123",
        recipient_type="user",
        sender_id="system",
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db_session.add(active_notification)
    db_session.commit()

    # Send request
    response = client.post("/notifications/clean-expired")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["deleted_count"] == 1

    # Check database
    notifications = db_session.query(Notification).all()
    assert len(notifications) == 1
    assert notifications[0].title == "Active"
