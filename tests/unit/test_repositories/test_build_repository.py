"""Tests for build repository implementation."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.entities import Build
from app.core.domain.enums import BuildStatus
from app.core.services.builds.models import BuildModel
from app.infrastructure.database.repositories.build_repository import SqlBuildRepository


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def build_repository(mock_session):
    """Create build repository with mock session."""
    return SqlBuildRepository(mock_session)


@pytest.fixture
def sample_build():
    """Create sample build entity."""
    return Build(
        name="test_build",
        tasks=["task1", "task2", "task3"],
        status=BuildStatus.PENDING,
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 12, 0, 0),
        error_message=None,
    )


@pytest.fixture
def sample_build_model():
    """Create sample build model."""
    return BuildModel(
        name="test_build",
        tasks=["task1", "task2", "task3"],
        status="pending",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 12, 0, 0),
        error_message=None,
    )


class TestSqlBuildRepository:
    """Test cases for SqlBuildRepository."""

    @pytest.mark.asyncio
    async def test_get_build_found(self, build_repository, mock_session, sample_build_model):
        """Test getting existing build."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_build_model
        mock_session.execute.return_value = mock_result

        result = await build_repository.get_build("test_build")

        assert result is not None
        assert result.name == "test_build"
        assert result.tasks == ["task1", "task2", "task3"]
        assert result.status == BuildStatus.PENDING
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_build_not_found(self, build_repository, mock_session):
        """Test getting non-existent build."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await build_repository.get_build("nonexistent")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_builds_multiple(self, build_repository, mock_session):
        """Test getting multiple builds."""
        build_models = [
            BuildModel(name="build1", tasks=["task1"], status="pending"),
            BuildModel(name="build2", tasks=["task1", "task2"], status="completed"),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = build_models
        mock_session.execute.return_value = mock_result

        result = await build_repository.get_builds(["build1", "build2"])

        assert len(result) == 2
        assert "build1" in result
        assert "build2" in result
        assert result["build1"].name == "build1"
        assert result["build2"].tasks == ["task1", "task2"]

    @pytest.mark.asyncio
    async def test_get_builds_empty_list(self, build_repository):
        """Test getting builds with empty list."""
        result = await build_repository.get_builds([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_all_builds(self, build_repository, mock_session):
        """Test getting all builds."""
        build_models = [
            BuildModel(name="build1", tasks=["task1"], status="pending"),
            BuildModel(name="build2", tasks=["task1", "task2"], status="completed"),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = build_models
        mock_session.execute.return_value = mock_result

        result = await build_repository.get_all_builds()

        assert len(result) == 2
        assert "build1" in result
        assert "build2" in result

    @pytest.mark.asyncio
    async def test_save_new_build(self, build_repository, mock_session, sample_build):
        """Test saving new build."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        await build_repository.save_build(sample_build)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_existing_build(self, build_repository, mock_session, sample_build, sample_build_model):
        """Test updating existing build."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_build_model
        mock_session.execute.return_value = mock_result

        await build_repository.save_build(sample_build)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_builds_multiple(self, build_repository, mock_session):
        """Test saving multiple builds."""
        builds = [
            Build(name="build1", tasks=["task1"]),
            Build(name="build2", tasks=["task1", "task2"]),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await build_repository.save_builds(builds)

        assert mock_session.add.call_count == 2
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_builds_empty_list(self, build_repository):
        """Test saving empty build list."""
        await build_repository.save_builds([])

    @pytest.mark.asyncio
    async def test_delete_build_success(self, build_repository, mock_session):
        """Test successful build deletion."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await build_repository.delete_build("test_build")

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_build_not_found(self, build_repository, mock_session):
        """Test deleting non-existent build."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await build_repository.delete_build("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_build_exists_true(self, build_repository, mock_session):
        """Test build exists check - positive case."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "test_build"
        mock_session.execute.return_value = mock_result

        result = await build_repository.build_exists("test_build")

        assert result is True

    @pytest.mark.asyncio
    async def test_build_exists_false(self, build_repository, mock_session):
        """Test build exists check - negative case."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await build_repository.build_exists("nonexistent")

        assert result is False

    def test_model_to_entity_conversion(self, build_repository):
        """Test conversion from model to entity."""
        model = BuildModel(
            name="test_build",
            tasks=["task1", "task2"],
            status="completed",
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 2),
            error_message="test error",
        )

        entity = build_repository._model_to_entity(model)

        assert entity.name == "test_build"
        assert entity.tasks == ["task1", "task2"]
        assert entity.status == BuildStatus.COMPLETED
        assert entity.error_message == "test error"

    def test_model_to_entity_string_tasks(self, build_repository):
        """Test conversion with string tasks (SQLite fallback)."""
        model = BuildModel(
            name="test_build",
            tasks="task1,task2",
            status="pending",
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 1),
        )

        entity = build_repository._model_to_entity(model)

        assert entity.tasks == ["task1", "task2"]

    def test_update_model_from_entity(self, build_repository, sample_build):
        """Test updating model from entity."""
        model = BuildModel(name="test_build")

        build_repository._update_model_from_entity(model, sample_build)

        assert model.tasks == ["task1", "task2", "task3"]
        assert model.status == "pending"
        assert model.error_message is None