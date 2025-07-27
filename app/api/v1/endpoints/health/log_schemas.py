"""Log management API schemas."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class LogStatisticsResponse(BaseModel):
    """Log statistics response schema."""
    
    task: str = Field(
        ...,
        description="Task name",
        example="get_log_statistics"
    )
    timestamp: str = Field(
        ...,
        description="Statistics collection timestamp",
        example="2023-01-01T12:00:00Z"
    )
    logs_directory: str = Field(
        ...,
        description="Path to logs directory",
        example="/app/logs"
    )
    total_size_mb: float = Field(
        ...,
        description="Total size of all logs in MB",
        example=45.67
    )
    files_count: Dict[str, int] = Field(
        ...,
        description="Count of different file types",
        example={
            "current_logs": 2,
            "rotated_logs": 5,
            "archives": 10,
            "total": 17
        }
    )
    current_logs: Dict[str, Any] = Field(
        ...,
        description="Current log files information",
        example={
            "saber.log": {
                "size_bytes": 8388608,
                "size_mb": 8.0,
                "modified": "2023-01-01T12:00:00"
            }
        }
    )
    rotated_logs: Dict[str, Any] = Field(
        ...,
        description="Rotated log files information"
    )
    archives: Dict[str, Any] = Field(
        ...,
        description="Archive files information"
    )


class LogArchiveResponse(BaseModel):
    """Log archiving response schema."""
    
    task: str = Field(
        ...,
        description="Task name",
        example="archive_old_logs"
    )
    timestamp: str = Field(
        ...,
        description="Task execution timestamp",
        example="2023-01-01T12:00:00Z"
    )
    task_id: str = Field(
        ...,
        description="Celery task ID for tracking",
        example="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    )
    status: str = Field(
        ...,
        description="Task execution status",
        example="started"
    )
    message: str = Field(
        ...,
        description="Status message",
        example="Log archiving task started successfully"
    )
    archives_created: int = Field(
        ...,
        description="Number of files archived (0 when started)",
        example=0
    )
    total_size_archived_mb: float = Field(
        ...,
        description="Total size archived in MB (0.0 when started)",
        example=0.0
    )


class LogCleanupResponse(BaseModel):
    """Log cleanup response schema."""
    
    task: str = Field(
        ...,
        description="Task name",
        example="cleanup_old_archives"
    )
    timestamp: str = Field(
        ...,
        description="Task execution timestamp",
        example="2023-01-01T12:00:00Z"
    )
    task_id: str = Field(
        ...,
        description="Celery task ID for tracking",
        example="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    )
    status: str = Field(
        ...,
        description="Task execution status",
        example="started"
    )
    message: str = Field(
        ...,
        description="Status message",
        example="Archive cleanup task started successfully"
    )
    retention_days: int = Field(
        ...,
        description="Archive retention period in days",
        example=7
    )
    archives_cleaned: int = Field(
        ...,
        description="Number of archives cleaned (0 when started)",
        example=0
    )
    space_freed_mb: float = Field(
        ...,
        description="Space freed in MB (0.0 when started)",
        example=0.0
    )