"""Common fixtures for integration tests."""

import asyncio
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from alembic import command
from alembic.config import Config
from pathlib import Path

from app.core.auth.entities import User, TokenPair
from app.core.domain.entities import Build, Task
from app.core.domain.enums import BuildStatus, TaskStatus


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_test_db():
    """Create a test database for async tests."""
    # Use file-based SQLite for tests to ensure tables persist
    test_db_path = "test_integration.sqlite"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{test_db_path}",
        poolclass=NullPool,
        echo=False,
    )
    
    # Run migrations for test database
    project_root = Path(__file__).parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    
    # Override database URL for tests
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{test_db_path}")
    
    # Create all tables using migrations
    command.upgrade(alembic_cfg, "head")
    
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
    
    # Clean up after tests
    await engine.dispose()
    
    # Remove test database file
    import os
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture(scope="function")
def client():
    """Create test client with mocked dependencies."""
    from tests.integration.test_app import create_test_app
    
    # Reset cached services before each test
    import app.api.dependencies as deps
    deps._auth_service = None
    deps._build_service = None
    
    # Create test app without database initialization
    app = create_test_app()
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$hashed_password_example",
        is_active=True,
    )


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for testing."""
    return User(
        id=2,
        username="admin",
        email="admin@example.com",
        hashed_password="$2b$12$hashed_password_admin",
        is_active=True,
    )


@pytest.fixture
def mock_token_pair():
    """Create a mock token pair for testing."""
    return TokenPair(
        access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.access",
        refresh_token="test_refresh_token",
        token_type="bearer",
        expires_in=1800,
    )


@pytest.fixture
def auth_headers():
    """Create authorization headers with a valid token."""
    return {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.access"}


@pytest.fixture
def mock_build():
    """Create a mock build for testing."""
    return Build(
        name="test_build",
        tasks=["task1", "task2", "task3"],
        status=BuildStatus.PENDING,
    )


@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    return Task(
        name="test_task",
        dependencies=set(),
        status=TaskStatus.PENDING,
    )


@pytest.fixture
def mock_auth_service():
    """Create a mock authentication service."""
    service = AsyncMock()
    service.register_user = AsyncMock()
    service.authenticate_user = AsyncMock()
    service.refresh_access_token = AsyncMock()
    service.get_current_user = AsyncMock()
    service.revoke_user_tokens = AsyncMock()
    return service


@pytest.fixture
def mock_build_service():
    """Create a mock build service."""
    service = AsyncMock()
    service.create_build = AsyncMock()
    service.get_build = AsyncMock()
    service.list_builds = AsyncMock()
    service.update_build = AsyncMock()
    service.delete_build = AsyncMock()
    service.execute_build = AsyncMock()
    service.get_all_builds = AsyncMock()
    service.get_build_status = AsyncMock()
    service.get_build_logs = AsyncMock()
    
    # Add task repository mock
    service._task_repository = AsyncMock()
    service._task_repository.get_task = AsyncMock()
    service._task_repository.get_all_tasks = AsyncMock()
    service._task_repository.save_task = AsyncMock()
    service._task_repository.delete_task = AsyncMock()
    
    # Add methods for topology
    service.get_topological_sort = AsyncMock()
    service.detect_cycles = AsyncMock()
    
    return service


@pytest.fixture
def mock_task_service():
    """Create a mock task service."""
    service = AsyncMock()
    service.create_task = AsyncMock()
    service.get_task = AsyncMock()
    service.list_tasks = AsyncMock()
    service.update_task = AsyncMock()
    service.delete_task = AsyncMock()
    return service


@pytest.fixture
def override_get_db(client, async_test_db):
    """Override the database dependency."""
    app = client.app
    
    async def _override_get_db():
        yield async_test_db
    
    from app.api.dependencies import get_database_session
    app.dependency_overrides[get_database_session] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_auth_dependency(client, mock_auth_service):
    """Override authentication service dependency."""
    app = client.app
    
    from app.api.dependencies import get_auth_service
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    yield mock_auth_service
    app.dependency_overrides.clear()


@pytest.fixture
def override_build_dependency(client, mock_build_service):
    """Override build service dependency."""
    app = client.app
    
    from app.api.dependencies import get_build_service
    app.dependency_overrides[get_build_service] = lambda: mock_build_service
    yield mock_build_service
    app.dependency_overrides.clear()


@pytest.fixture
def override_current_user(client, mock_user):
    """Override current user dependency."""
    app = client.app
    
    from app.api.dependencies import get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.clear()


@pytest.fixture
def disable_auth(client):
    """Disable authentication for tests that don't need it."""
    app = client.app
    
    from app.api.dependencies import get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client, mock_user):
    """Create test client with authenticated user."""
    app = client.app
    
    from app.api.dependencies import get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    yield client
    app.dependency_overrides.clear()