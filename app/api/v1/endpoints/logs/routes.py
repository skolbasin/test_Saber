"""Log management API routes."""

from datetime import datetime
from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_active_user
from .schemas import LogStatisticsResponse, LogArchiveResponse, LogCleanupResponse
from app.infrastructure.tasks.log_management import (
    get_log_statistics,
    archive_old_logs,
    cleanup_old_archives
)
from app.core.auth.entities import User

router = APIRouter(prefix="/logs", tags=["Log Management"])


@router.get(
    "/statistics",
    response_model=LogStatisticsResponse,
    summary="Get log file statistics",
    description="Get detailed statistics about log files, rotated logs, and archives.",
    responses={
        200: {"description": "Log statistics retrieved successfully"},
        401: {"description": "Authentication required"},
    },
)
async def get_log_file_statistics(
    current_user: User = Depends(get_current_active_user),
) -> LogStatisticsResponse:
    """
    Get detailed statistics about log files.
    
    Returns information about current logs, rotated logs, and archives
    including file sizes and modification dates.
    """
    # Execute Celery task synchronously for immediate response
    result = get_log_statistics.apply()
    return LogStatisticsResponse(**result.result)


@router.post(
    "/archive",
    response_model=LogArchiveResponse,
    summary="Archive old log files",
    description="Manually trigger archiving of old rotated log files.",
    responses={
        200: {"description": "Log archiving started"},
        401: {"description": "Authentication required"},
    },
)
async def trigger_log_archiving(
    current_user: User = Depends(get_current_active_user),
) -> LogArchiveResponse:
    """
    Manually trigger archiving of old log files.
    
    Compresses and archives rotated log files older than 1 day.
    This operation is normally performed automatically daily at 2 AM.
    """
    # Execute Celery task asynchronously
    task = archive_old_logs.delay()
    
    # Return immediately with task info
    return LogArchiveResponse(
        task="archive_old_logs",
        timestamp=datetime.utcnow().isoformat() + "Z",
        task_id=task.id,
        status="started",
        message="Log archiving task started successfully",
        archives_created=0,
        total_size_archived_mb=0.0
    )


@router.post(
    "/cleanup",
    response_model=LogCleanupResponse,
    summary="Clean up old archives",
    description="Manually trigger cleanup of old archived log files.",
    responses={
        200: {"description": "Archive cleanup started"},
        401: {"description": "Authentication required"},
    },
)
async def trigger_archive_cleanup(
    retention_days: int = 7,
    current_user: User = Depends(get_current_active_user),
) -> LogCleanupResponse:
    """
    Manually trigger cleanup of old archive files.
    
    Simulates uploading archives to external storage and removes them locally.
    This operation is normally performed automatically daily at 3 AM.
    
    Args:
        retention_days: Number of days to keep archives before cleanup (default: 7)
    """
    # Execute Celery task asynchronously
    task = cleanup_old_archives.delay(retention_days=retention_days)
    
    # Return immediately with task info
    return LogCleanupResponse(
        task="cleanup_old_archives",
        timestamp=datetime.utcnow().isoformat() + "Z",
        task_id=task.id,
        status="started",
        message="Archive cleanup task started successfully",
        retention_days=retention_days,
        archives_cleaned=0,
        space_freed_mb=0.0
    )