"""
Router for the logging module.
"""

# import json # Removed json import
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.logging.models import LogEntryCreate, LogEntryResponse, LogQueryParams
from app.modules.logging.service import LoggingService

router = APIRouter()


@router.post("/", response_model=LogEntryResponse, status_code=201)
async def create_log_entry(log_entry: LogEntryCreate, db: Session = Depends(get_db)):
    """
    Create a new log entry.
    """
    return await LoggingService.create_log_entry(db, log_entry)


@router.get("/", response_model=List[LogEntryResponse])
async def get_log_entries(
    level: Optional[str] = Query(None, description="Filter by log level"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db),
):
    """
    Get log entries with optional filtering.
    """
    query_params = LogQueryParams(
        level=level,
        service=service,
        start_time=start_time,
        end_time=end_time,
        trace_id=trace_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return await LoggingService.get_log_entries(db, query_params)


@router.get("/{log_id}", response_model=LogEntryResponse)
async def get_log_entry(log_id: int, db: Session = Depends(get_db)):
    """
    Get a specific log entry by ID.
    """
    log_entry = await LoggingService.get_log_entry_by_id(db, log_id)
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return log_entry


@router.get("/export/json")
async def export_logs_to_json(
    level: Optional[str] = Query(None, description="Filter by log level"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of logs to export"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db),
):
    """
    Export logs to JSON format.
    """
    query_params = LogQueryParams(
        level=level,
        service=service,
        start_time=start_time,
        end_time=end_time,
        trace_id=trace_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    logs_json = await LoggingService.export_logs_to_json(db, query_params)

    response = Response(content=logs_json, media_type="application/json")
    response.headers["Content-Disposition"] = (
        f"attachment; filename=logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    return response


@router.get("/stats/summary")
async def get_log_statistics(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    db: Session = Depends(get_db),
):
    """
    Get statistics about log entries.
    """
    return await LoggingService.get_log_statistics(db, start_time=start_time, end_time=end_time)
