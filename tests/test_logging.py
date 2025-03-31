"""
Tests for the logging module.
"""

import json
from datetime import datetime, timedelta

from app.modules.logging.models import LogEntry, LogEntryCreate, LogLevel
from app.modules.logging.service import LoggingService


def test_create_log_entry(client, db_session):
    """Test creating a log entry."""
    # Create log entry data
    log_data = {
        "level": "INFO",
        "message": "Test log message",
        "source": "test_service",
        "context": {"test_key": "test_value"},
    }

    # Send request
    response = client.post("/logs/", json=log_data)

    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["level"] == log_data["level"]
    assert data["message"] == log_data["message"]
    assert data["source"] == log_data["source"]
    assert data["context"] == log_data["context"]

    # Check database
    db_log = db_session.query(LogEntry).filter(LogEntry.id == data["id"]).first()
    assert db_log is not None
    assert db_log.level == log_data["level"]
    assert db_log.message == log_data["message"]


def test_get_log_entries(client, db_session):
    """Test getting log entries."""
    # Create test log entries
    for i in range(3):
        log_entry = LogEntry(
            level=LogLevel.INFO.value,
            message=f"Test message {i}",
            source="test_service",
            context={"test_key": f"test_value_{i}"},
        )
        db_session.add(log_entry)
    db_session.commit()

    # Send request
    response = client.get("/logs/")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["source"] == "test_service"


def test_get_log_entries_with_filters(client, db_session):
    """Test getting log entries with filters."""
    # Create test log entries with different levels
    levels = [LogLevel.INFO.value, LogLevel.WARNING.value, LogLevel.ERROR.value]
    for i, level in enumerate(levels):
        log_entry = LogEntry(
            level=level,
            message=f"Test message {i}",
            source="test_service",
            context={"test_key": f"test_value_{i}"},
        )
        db_session.add(log_entry)
    db_session.commit()

    # Send request with level filter
    response = client.get("/logs/?level=WARNING")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["level"] == "WARNING"


def test_get_log_entries_with_time_range(client, db_session):
    """Test getting log entries within a time range."""
    # Create test log entry from yesterday
    yesterday = datetime.utcnow() - timedelta(days=1)
    old_log = LogEntry(
        level=LogLevel.INFO.value,
        message="Old log message",
        source="test_service",
        context={"test_key": "old_value"},
        created_at=yesterday,
    )
    db_session.add(old_log)

    # Create test log entry from today
    new_log = LogEntry(
        level=LogLevel.INFO.value,
        message="New log message",
        source="test_service",
        context={"test_key": "new_value"},
    )
    db_session.add(new_log)
    db_session.commit()

    # Format time for query
    start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()

    # Send request with time range
    response = client.get(f"/logs/?start_time={start_time}")

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["message"] == "New log message"


def test_export_logs(client, db_session):
    """Test exporting logs to JSON."""
    # Create test log entries
    for i in range(3):
        log_entry = LogEntry(
            level=LogLevel.INFO.value,
            message=f"Test message {i}",
            source="test_service",
            context={"test_key": f"test_value_{i}"},
        )
        db_session.add(log_entry)
    db_session.commit()

    # Send request
    response = client.get("/logs/export")

    # Check response
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["Content-Disposition"].startswith(
        "attachment; filename=logs_"
    )

    # Parse JSON response
    logs = json.loads(response.content)
    assert len(logs) == 3
    assert all("message" in log for log in logs)
    assert all("level" in log for log in logs)
    assert all("source" in log for log in logs)


def test_log_entry_service_methods(db_session):
    """Test LoggingService methods directly."""
    # Create log entry using service
    log_entry_create = LogEntryCreate(
        level=LogLevel.ERROR,
        message="Service test message",
        source="test_service",
        context={"test_key": "service_test_value"},
    )

    log_entry = LoggingService.create_log_entry(db_session, log_entry_create)

    # Check created log entry
    assert log_entry.level == LogLevel.ERROR.value
    assert log_entry.message == "Service test message"

    # Get log entries using service
    from app.modules.logging.models import LogQueryParams

    query_params = LogQueryParams(level=LogLevel.ERROR, source="test_service", limit=10)

    log_entries = LoggingService.get_log_entries(db_session, query_params)

    # Check retrieved log entries
    assert len(log_entries) == 1
    assert log_entries[0].level == LogLevel.ERROR.value
    assert log_entries[0].source == "test_service"
