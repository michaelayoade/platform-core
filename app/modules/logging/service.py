"""
Service for the logging module.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.modules.logging.models import LogEntry, LogEntryCreate, LogQueryParams
from app.utils.common import json_serializer


class LoggingService:
    """
    Service for managing structured application logs.
    """

    @staticmethod
    async def create_log_entry(db: Session, log_entry: LogEntryCreate) -> LogEntry:
        """
        Create a new log entry.

        Args:
            db: Database session
            log_entry: Log entry data

        Returns:
            Created log entry
        """
        db_log_entry = LogEntry(
            level=log_entry.level,
            service=log_entry.service,
            message=log_entry.message,
            context=log_entry.context,
            trace_id=log_entry.trace_id,
            span_id=log_entry.span_id,
            user_id=log_entry.user_id,
            ip_address=log_entry.ip_address,
        )
        db.add(db_log_entry)
        db.commit()
        db.refresh(db_log_entry)
        return db_log_entry

    @staticmethod
    async def get_log_entries(
        db: Session, query_params: LogQueryParams
    ) -> List[LogEntry]:
        """
        Get log entries based on query parameters.

        Args:
            db: Database session
            query_params: Query parameters

        Returns:
            List of log entries
        """
        query = db.query(LogEntry)

        # Apply filters
        if query_params.level:
            query = query.filter(LogEntry.level == query_params.level)

        if query_params.service:
            query = query.filter(LogEntry.service == query_params.service)

        if query_params.trace_id:
            query = query.filter(LogEntry.trace_id == query_params.trace_id)

        if query_params.user_id:
            query = query.filter(LogEntry.user_id == query_params.user_id)

        # Apply time range filters
        if query_params.start_time and query_params.end_time:
            query = query.filter(
                and_(
                    LogEntry.timestamp >= query_params.start_time,
                    LogEntry.timestamp <= query_params.end_time,
                )
            )
        elif query_params.start_time:
            query = query.filter(LogEntry.timestamp >= query_params.start_time)
        elif query_params.end_time:
            query = query.filter(LogEntry.timestamp <= query_params.end_time)

        # Order by timestamp (newest first)
        query = query.order_by(desc(LogEntry.timestamp))

        # Apply pagination
        query = query.limit(query_params.limit).offset(query_params.offset)

        return query.all()

    @staticmethod
    async def get_log_entry_by_id(db: Session, log_id: int) -> Optional[LogEntry]:
        """
        Get a log entry by ID.

        Args:
            db: Database session
            log_id: Log entry ID

        Returns:
            Log entry if found, None otherwise
        """
        return db.query(LogEntry).filter(LogEntry.id == log_id).first()

    @staticmethod
    async def export_logs_to_json(db: Session, query_params: LogQueryParams) -> str:
        """
        Export logs to JSON format.

        Args:
            db: Database session
            query_params: Query parameters

        Returns:
            JSON string of log entries
        """
        log_entries = await LoggingService.get_log_entries(db, query_params)

        # Convert to dict format for JSON serialization
        log_dicts = []
        for log in log_entries:
            log_dict = {
                "id": log.id,
                "timestamp": log.timestamp,
                "level": log.level,
                "service": log.service,
                "message": log.message,
                "context": log.context,
                "trace_id": log.trace_id,
                "span_id": log.span_id,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
            }
            log_dicts.append(log_dict)

        # Serialize to JSON
        return json.dumps(log_dicts, default=json_serializer)

    @staticmethod
    async def get_log_statistics(
        db: Session,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about log entries.

        Args:
            db: Database session
            start_time: Optional start time for filtering
            end_time: Optional end time for filtering

        Returns:
            Dictionary of log statistics
        """
        # Base query
        query = db.query(LogEntry)

        # Apply time range filters if provided
        if start_time and end_time:
            query = query.filter(
                and_(LogEntry.timestamp >= start_time, LogEntry.timestamp <= end_time)
            )
        elif start_time:
            query = query.filter(LogEntry.timestamp >= start_time)
        elif end_time:
            query = query.filter(LogEntry.timestamp <= end_time)

        # Get total count
        total_count = query.count()

        # Get counts by level
        level_counts = {}
        for level in ["INFO", "WARNING", "ERROR", "DEBUG", "CRITICAL"]:
            level_count = query.filter(LogEntry.level == level).count()
            if level_count > 0:
                level_counts[level] = level_count

        # Get counts by service
        service_counts = {}
        services = db.query(LogEntry.service).distinct().all()
        for service in services:
            service_name = service[0]
            service_count = query.filter(LogEntry.service == service_name).count()
            service_counts[service_name] = service_count

        # Return statistics
        return {
            "total_count": total_count,
            "by_level": level_counts,
            "by_service": service_counts,
        }
