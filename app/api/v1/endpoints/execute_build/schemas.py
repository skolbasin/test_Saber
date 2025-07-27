"""Execute build endpoint schemas."""

from pydantic import BaseModel, Field
from typing import Optional


class ExecuteBuildRequest(BaseModel):
    """Request schema for executing a build."""
    
    build: str = Field(
        ...,
        min_length=1,
        description="Name of the build to execute",
        example="frontend_build"
    )
    
    algorithm: Optional[str] = Field(
        None,
        description="Sorting algorithm to use (kahn or dfs)",
        example="kahn"
    )


class ExecuteBuildResponse(BaseModel):
    """Response schema for build execution."""
    
    build_name: str = Field(
        ...,
        description="Name of the executed build",
        example="frontend_build"
    )
    
    status: str = Field(
        ...,
        description="Current status of the build",
        example="running"
    )
    
    message: str = Field(
        ...,
        description="Status message",
        example="Build execution started successfully"
    )