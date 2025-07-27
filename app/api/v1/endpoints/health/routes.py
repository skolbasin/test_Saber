"""Health check API routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database_session
from .schemas import HealthResponse, DetailedHealthResponse, ReadinessResponse, LivenessResponse  
from app.infrastructure.cache.redis_client import get_redis_client

router = APIRouter(prefix="/health", tags=["Health Check"])


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Simple health check endpoint.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
)
async def basic_health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns minimal health status information without dependency checks.
    Useful for load balancer health checks.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health check",
    description="Check the health status of the application and its dependencies.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
)
async def detailed_health_check(
    session: AsyncSession = Depends(get_database_session),
) -> DetailedHealthResponse:
    """
    Perform detailed health check of the application and its dependencies.
    
    Checks the status of:
    - Database connectivity
    - Redis connectivity (if configured)
    - Celery workers (if configured)
    
    Returns overall health status and individual service statuses.
    """
    services = {}
    overall_status = "healthy"
    
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"
        overall_status = "unhealthy"
    
    try:
        redis_client = get_redis_client()
        redis_healthy = await redis_client.ping()
        services["redis"] = "healthy" if redis_healthy else "unhealthy"
        if not redis_healthy:
            overall_status = "unhealthy"
    except Exception:
        services["redis"] = "unhealthy"
        overall_status = "unhealthy"
    
    services["celery"] = "not_configured"
    
    return DetailedHealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        services=services,
        uptime="unknown",
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Check if the application is ready to serve requests.",
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service is not ready"},
    },
)
async def readiness_check(
    session: AsyncSession = Depends(get_database_session),
) -> ReadinessResponse:
    """
    Readiness probe for Kubernetes deployments.
    
    Checks if the application is ready to accept traffic by verifying
    that all critical dependencies are available and responsive.
    """
    checks = {}
    ready = True
    
    try:
        from sqlalchemy import text
        import time
        start_time = time.perf_counter()
        await session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start_time) * 1000
        checks["database"] = {"status": "ready", "latency_ms": round(latency, 2)}
    except Exception as e:
        checks["database"] = {"status": "not_ready", "error": str(e)}
        ready = False
    
    try:
        redis_client = get_redis_client()
        import time
        start_time = time.perf_counter()
        await redis_client.ping()
        latency = (time.perf_counter() - start_time) * 1000
        checks["redis"] = {"status": "ready", "latency_ms": round(latency, 2)}
    except Exception as e:
        checks["redis"] = {"status": "not_ready", "error": str(e)}
        ready = False
    
    return ReadinessResponse(
        ready=ready,
        checks=checks,
    )


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness check",
    description="Check if the application is alive and responsive.",
    responses={
        200: {"description": "Service is alive"},
    },
)
async def liveness_check() -> LivenessResponse:
    """
    Liveness probe for Kubernetes deployments.
    
    Simple endpoint that indicates the application process is alive
    and responsive. Does not check dependencies.
    """
    return LivenessResponse(
        alive=True,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


