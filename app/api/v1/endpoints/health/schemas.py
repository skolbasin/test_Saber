"""Health check API schemas."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Basic health check response schema."""
    
    status: str = Field(
        ...,
        description="Service health status",
        example="healthy"
    )
    timestamp: str = Field(
        ...,
        description="Response timestamp",
        example="2023-01-01T12:00:00Z"
    )


class DetailedHealthResponse(BaseModel):
    """Detailed health check response schema."""
    
    status: str = Field(
        ...,
        description="Overall service health status",
        example="healthy"
    )
    timestamp: str = Field(
        ...,
        description="Response timestamp",
        example="2023-01-01T12:00:00Z"
    )
    services: Dict[str, str] = Field(
        ...,
        description="Status of individual services",
        example={
            "database": "healthy",
            "redis": "healthy",
            "external_api": "degraded"
        }
    )
    version: str = Field(
        ...,
        description="Application version",
        example="1.0.0"
    )
    uptime: str = Field(
        ...,
        description="Service uptime",
        example="2 days, 14:30:15"
    )


class ReadinessResponse(BaseModel):
    """Readiness check response schema."""
    
    ready: bool = Field(
        ...,
        description="Whether service is ready to accept requests",
        example=True
    )
    checks: Dict[str, Any] = Field(
        ...,
        description="Individual readiness checks",
        example={
            "database": {"status": "ready", "latency_ms": 5.2},
            "redis": {"status": "ready", "latency_ms": 1.1}
        }
    )


class LivenessResponse(BaseModel):
    """Liveness check response schema."""
    
    alive: bool = Field(
        ...,
        description="Whether service is alive",
        example=True
    )
    timestamp: str = Field(
        ...,
        description="Response timestamp",
        example="2023-01-01T12:00:00Z"
    )