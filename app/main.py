"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.auth.routes import router as auth_router
from app.api.v1.endpoints.health.routes import router as health_router
from app.api.v1.endpoints.logs.routes import router as logs_router
from app.api.v1.endpoints.tasks.routes import router as tasks_router
from app.api.v1.endpoints.builds.routes import router as builds_router
from app.api.v1.endpoints.topology.routes import router as topology_router
from app.api.v1.endpoints.get_tasks.routes import router as get_tasks_router
from app.api.v1.endpoints.execute_build.routes import router as execute_build_router
from app.api.v1.endpoints.get_build_status.routes import router as get_build_status_router
from app.core.exceptions import (
    DomainException,
    BuildNotFoundException,
    TaskNotFoundException,
    CircularDependencyException,
)
from app.infrastructure.cache.redis_client import get_redis_client
from app.utils.logging import setup_logging
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger = logging.getLogger("app")
    logger.info("Starting Saber Build System...")

    try:
        setup_logging()
        logger.info("Logging configured")

        settings = get_settings()

        # Init DB (without Alembic)
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.infrastructure.database.connection import Base

        engine = create_async_engine(settings.database_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
        logger.info("Database tables created")

        # Redis init
        redis_client = get_redis_client()
        await redis_client.connect()
        if await redis_client.ping():
            logger.info("Redis connection established")
        else:
            logger.warning("Redis ping failed")

        app.state.redis_client = redis_client

        # Load initial data from YAML files
        from app.infrastructure.services.yaml_loader import load_initial_data_to_db
        await load_initial_data_to_db(engine)
        logger.info("Initial data loaded from YAML files")

        logger.info("Saber Build System started successfully")

    except Exception as e:
        logger.exception("Startup failed")
        raise

    yield

    logger.info("Shutting down Saber Build System...")

    try:
        redis_client = getattr(app.state, "redis_client", None)
        if redis_client:
            await redis_client.disconnect()
            logger.info("Redis connection closed")
    except Exception as e:
        logger.exception("Shutdown error")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Saber Build System",
        description="Enterprise build system microservice with topological task ordering",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(logs_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(builds_router, prefix="/api/v1")
    app.include_router(topology_router, prefix="/api/v1")
    app.include_router(get_tasks_router, prefix="/api/v1")
    app.include_router(execute_build_router, prefix="/api/v1")
    app.include_router(get_build_status_router, prefix="/api/v1")

    register_exception_handlers(app)

    register_middleware(app)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers."""

    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        """Handle custom domain exceptions."""
        return JSONResponse(
            status_code=400,
            content={"error": exc.message, "type": exc.__class__.__name__},
        )

    @app.exception_handler(BuildNotFoundException)
    async def build_not_found_handler(request: Request, exc: BuildNotFoundException):
        """Handle build not found exceptions."""
        return JSONResponse(
            status_code=404,
            content={"error": str(exc), "type": "BuildNotFound"},
        )

    @app.exception_handler(TaskNotFoundException)
    async def task_not_found_handler(request: Request, exc: TaskNotFoundException):
        """Handle task not found exceptions."""
        return JSONResponse(
            status_code=404,
            content={"error": str(exc), "type": "TaskNotFound"},
        )

    @app.exception_handler(CircularDependencyException)
    async def circular_dependency_handler(request: Request, exc: CircularDependencyException):
        """Handle circular dependency exceptions."""
        return JSONResponse(
            status_code=400,
            content={"error": exc.message, "cycle": exc.cycle, "type": "CircularDependency"},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "type": "HTTPException"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger = logging.getLogger("app")
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "type": "InternalError"},
        )


def register_middleware(app: FastAPI) -> None:
    """Register custom middleware."""

    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """Log all HTTP requests."""
        logger = logging.getLogger("app")

        import time
        start_time = request.state.start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        logger.info(f"Request started: {request.method} {request.url.path} from {client_ip}")

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"status={response.status_code} time={process_time:.3f}s"
        )

        return response

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        """Add security headers to responses."""
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


app = create_app()


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "message": "Saber Build System API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "saber-build-system"}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )