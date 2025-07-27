"""Get build status endpoint schemas."""

from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime


class GetBuildStatusRequest(BaseModel):
    """Request schema for getting build status."""
    
    build: str = Field(
        ...,
        min_length=1,
        description="Name of the build to check status",
        example="frontend_build"
    )


class BuildStatusResponse(BaseModel):
    """Response schema for build status."""
    
    build_name: str = Field(
        ...,
        description="Name of the build",
        example="frontend_build"
    )
    
    status: str = Field(
        ...,
        description="Current status of the build",
        example="completed"
    )
    
    created_at: Optional[datetime] = Field(
        None,
        description="When the build was created",
        example="2025-07-26T10:30:00Z"
    )
    
    tasks: list[str] = Field(
        ...,
        description="List of tasks in the build",
        example=["compile_exe", "pack_build"]
    )
    
    task_statuses: Optional[Dict[str, str]] = Field(
        None,
        description="Status of each task in the build",
        example={"compile_exe": "completed", "pack_build": "completed"}
    )