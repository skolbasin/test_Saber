"""Task management API schemas."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.core.domain.enums import TaskStatus


class TaskCreateRequest(BaseModel):
    """Task creation request schema."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Task name (must be unique)",
        example="compile_frontend"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task names this task depends on",
        example=["setup_environment", "install_dependencies"]
    )

    @field_validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Task name cannot be empty')
        return v.strip()

    @field_validator('dependencies')
    def validate_dependencies(cls, v):
        # Remove duplicates and empty strings
        return [dep.strip() for dep in v if dep and dep.strip()]


class TaskUpdateRequest(BaseModel):
    """Task update request schema."""
    
    dependencies: Optional[List[str]] = Field(
        None,
        description="Updated list of task dependencies",
        example=["setup_environment"]
    )
    status: Optional[TaskStatus] = Field(
        None,
        description="Updated task status",
        example="completed"
    )

    @field_validator('dependencies')
    def validate_dependencies(cls, v):
        if v is not None:
            return [dep.strip() for dep in v if dep and dep.strip()]
        return v


class TaskResponse(BaseModel):
    """Task response schema."""
    
    name: str = Field(
        ...,
        description="Task name",
        example="compile_frontend"
    )
    dependencies: List[str] = Field(
        ...,
        description="List of task dependencies",
        example=["setup_environment", "install_dependencies"]
    )
    status: str = Field(
        ...,
        description="Current task status",
        example="pending"
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Task creation timestamp",
        example="2023-01-01T12:00:00Z"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Last task update timestamp", 
        example="2023-01-01T12:00:00Z"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error details if task failed",
        example="Compilation failed: missing dependency"
    )

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Task list response schema."""
    
    tasks: List[TaskResponse] = Field(
        ...,
        description="List of tasks",
    )
    total: int = Field(
        ...,
        description="Total number of tasks",
        example=10
    )


class TaskExecutionRequest(BaseModel):
    """Task execution request schema."""
    
    async_execution: bool = Field(
        default=True,
        description="Whether to execute task asynchronously",
        example=True
    )
    force_restart: bool = Field(
        default=False,
        description="Force restart if task is already running",
        example=False
    )


class TaskExecutionResponse(BaseModel):
    """Task execution response schema."""
    
    task_name: str = Field(
        ...,
        description="Name of the executed task",
        example="compile_frontend"
    )
    execution_id: str = Field(
        ...,
        description="Unique execution identifier",
        example="exec_12345"
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
    async_execution: bool = Field(
        ...,
        description="Whether execution is asynchronous",
        example=True
    )