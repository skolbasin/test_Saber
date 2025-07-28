"""Test application setup for integration tests."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.auth.routes import router as auth_router
from app.api.v1.endpoints.health.routes import router as health_router
from app.api.v1.endpoints.logs.routes import router as logs_router
from app.api.v1.endpoints.tasks.routes import router as tasks_router
from app.api.v1.endpoints.builds.routes import router as builds_router
from app.api.v1.endpoints.topology.routes import router as topology_router
from app.api.v1.endpoints.get_tasks.routes import router as get_tasks_router
from app.api.v1.endpoints.execute_build.routes import router as execute_build_router
from app.api.v1.endpoints.get_build_status.routes import router as get_build_status_router
from app.settings import get_settings


@asynccontextmanager
async def _test_lifespan(app: FastAPI):
    """Test lifespan that doesn't initialize database."""
    # Startup
    yield
    # Shutdown


def create_test_app() -> FastAPI:
    """Create FastAPI app for testing without database initialization."""
    settings = get_settings()
    
    app = FastAPI(
        title="Saber Build System Test",
        description="Test instance",
        version="1.0.0",
        lifespan=_test_lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(logs_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(builds_router, prefix="/api/v1")
    app.include_router(topology_router, prefix="/api/v1")
    app.include_router(get_tasks_router, prefix="/api/v1")
    app.include_router(execute_build_router, prefix="/api/v1")
    app.include_router(get_build_status_router, prefix="/api/v1")
    
    return app