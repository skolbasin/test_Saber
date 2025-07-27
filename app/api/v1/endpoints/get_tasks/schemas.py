"""Schemas for get_tasks endpoint."""

from typing import List
from pydantic import BaseModel, Field, RootModel


class GetTasksRequest(BaseModel):
    """Request schema for get_tasks endpoint."""
    
    build: str = Field(
        ...,
        description="Name of the build to get tasks for",
        min_length=1,
        example="make_tests"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "build": "make_tests"
            }
        }
    }


class GetTasksResponse(RootModel[List[str]]):
    """Response schema for get_tasks endpoint - just a list of task names."""
    
    model_config = {
        "json_schema_extra": {
            "example": [
                "compile_exe",
                "pack_build"
            ]
        }
    }