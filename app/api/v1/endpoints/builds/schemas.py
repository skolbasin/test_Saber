"""Build management API schemas."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.core.domain.enums import BuildStatus


class BuildCreateRequest(BaseModel):
    """Build creation request schema."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Build name (must be unique)",
        example="frontend_build"
    )
    tasks: List[str] = Field(
        ...,
        min_items=1,
        description="List of task names included in this build",
        example=["compile_core", "compile_ui", "run_tests"]
    )

    @field_validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Build name cannot be empty')
        return v.strip()

    @field_validator('tasks')
    def validate_tasks(cls, v):
        if not v:
            raise ValueError('Build must contain at least one task')
        # Remove duplicates and empty strings
        clean_tasks = [task.strip() for task in v if task and task.strip()]
        if not clean_tasks:
            raise ValueError('Build must contain at least one valid task')
        return clean_tasks


class BuildUpdateRequest(BaseModel):
    """Build update request schema."""
    
    tasks: Optional[List[str]] = Field(
        None,
        description="Updated list of task names",
        example=["compile_core", "compile_ui", "run_tests", "package"]
    )
    status: Optional[BuildStatus] = Field(
        None,
        description="Updated build status",
        example="running"
    )

    @field_validator('tasks')
    def validate_tasks(cls, v):
        if v is not None:
            if not v:
                raise ValueError('Build must contain at least one task')
            return [task.strip() for task in v if task and task.strip()]
        return v


class BuildResponse(BaseModel):
    """Build response schema."""
    
    name: str = Field(
        ...,
        description="Build name",
        example="frontend_build"
    )
    tasks: List[str] = Field(
        ...,
        description="List of task names in this build",
        example=["compile_core", "compile_ui", "run_tests"]
    )
    status: str = Field(
        ...,
        description="Current build status",
        example="pending"
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Build creation timestamp",
        example="2023-01-01T12:00:00Z"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Last build update timestamp",
        example="2023-01-01T12:00:00Z"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error details if build failed",
        example="Task 'compile_ui' failed: syntax error"
    )

    class Config:
        from_attributes = True


class BuildListResponse(BaseModel):
    """Build list response schema."""
    
    builds: List[BuildResponse] = Field(
        ...,
        description="List of builds",
    )
    total: int = Field(
        ...,
        description="Total number of builds",
        example=5
    )


class BuildExecutionRequest(BaseModel):
    """Build execution request schema."""
    
    async_execution: bool = Field(
        default=True,
        description="Whether to execute build asynchronously",
        example=True
    )
    force_restart: bool = Field(
        default=False,
        description="Force restart if build is already running",
        example=False
    )


class BuildExecutionResponse(BaseModel):
    """Build execution response schema."""
    
    build_name: str = Field(
        ...,
        description="Name of the executed build",
        example="frontend_build"
    )
    execution_id: str = Field(
        ...,
        description="Unique execution identifier",
        example="exec_build_12345"
    )
    status: str = Field(
        ...,
        description="Current execution status",
        example="running"
    )
    started_at: datetime = Field(
        ...,
        description="Execution start timestamp",
        example="2023-01-01T12:00:00Z"
    )
    estimated_duration: Optional[int] = Field(
        None,
        description="Estimated execution time in seconds",
        example=300
    )
    async_execution: bool = Field(
        ...,
        description="Whether execution is asynchronous",
        example=True
    )