"""Topology analysis API schemas."""

from typing import List
from pydantic import BaseModel, Field


class SortResultResponse(BaseModel):
    """Topology sort result response schema."""
    
    build_name: str = Field(
        ...,
        description="Name of the sorted build",
        example="frontend_build"
    )
    sorted_tasks: List[str] = Field(
        ...,
        description="Tasks in topological execution order",
        example=["compile_core", "compile_ui", "run_tests", "package"]
    )
    algorithm_used: str = Field(
        ...,
        description="Algorithm used for sorting",
        example="kahn"
    )
    execution_time_ms: float = Field(
        ...,
        description="Time taken for sorting in milliseconds",
        example=1.23
    )
    total_tasks: int = Field(
        ...,
        description="Total number of tasks sorted",
        example=4
    )
    has_cycles: bool = Field(
        ...,
        description="Whether circular dependencies were detected",
        example=False
    )
    cycles: List[List[str]] = Field(
        ...,
        description="Detected cycles (if any)",
        example=[]
    )


class CycleDetectionResponse(BaseModel):
    """Cycle detection response schema."""
    
    build_name: str = Field(
        ...,
        description="Name of the analyzed build",
        example="frontend_build"
    )
    has_cycles: bool = Field(
        ...,
        description="Whether circular dependencies were found",
        example=False
    )
    cycles: List[List[str]] = Field(
        ...,
        description="List of detected cycles",
        example=[]
    )
    total_cycles: int = Field(
        ...,
        description="Total number of cycles found",
        example=0
    )
    analysis_method: str = Field(
        ...,
        description="Method used for cycle detection",
        example="depth_first_search"
    )


class ValidationResponse(BaseModel):
    """Build validation response schema."""
    
    build_name: str = Field(
        ...,
        description="Name of the validated build",
        example="frontend_build"
    )
    is_valid: bool = Field(
        ...,
        description="Whether the build is valid",
        example=True
    )
    has_cycles: bool = Field(
        ...,
        description="Whether circular dependencies exist",
        example=False
    )
    cycles: List[List[str]] = Field(
        ...,
        description="Detected cycles",
        example=[]
    )
    missing_tasks: List[str] = Field(
        ...,
        description="Tasks referenced but not found",
        example=[]
    )
    total_tasks: int = Field(
        ...,
        description="Total number of tasks in build",
        example=4
    )
    sort_possible: bool = Field(
        ...,
        description="Whether topological sort is possible",
        example=True
    )
    suggested_order: List[str] = Field(
        ...,
        description="Suggested execution order (if sort possible)",
        example=["compile_core", "compile_ui", "run_tests", "package"]
    )
    validation_timestamp: str = Field(
        ...,
        description="When validation was performed",
        example="2023-01-01T12:00:00Z"
    )