"""Tests for task repository implementation."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.entities import Task
from app.core.domain.enums import TaskStatus
from app.core.services.tasks.models import TaskModel
from app.infrastructure.database.repositories.task_repository import SqlTaskRepository


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def task_repository(mock_session):
    """Create task repository with mock session."""
    return SqlTaskRepository(mock_session)


@pytest.fixture
def sample_task():
    """Create sample task entity."""
    return Task(
        name="test_task",
        dependencies={"dep1", "dep2"},
        status=TaskStatus.PENDING,
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 12, 0, 0),
        error_message=None,
    )


@pytest.fixture
def sample_task_model():
    """Create sample task model."""
    return TaskModel(
        name="test_task",
        dependencies=["dep1", "dep2"],
        status="pending",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 12, 0, 0),
        error_message=None,
    )


class TestSqlTaskRepository:
    """Test cases for SqlTaskRepository."""

    @pytest.mark.asyncio
    async def test_get_task_found(self, task_repository, mock_session, sample_task_model):
        """Test getting existing task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task_model
        mock_session.execute.return_value = mock_result

        result = await task_repository.get_task("test_task")

        assert result is not None
        assert result.name == "test_task"
        assert result.dependencies == {"dep1", "dep2"}
        assert result.status == TaskStatus.PENDING
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_repository, mock_session):
        """Test getting non-existent task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await task_repository.get_task("nonexistent")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tasks_multiple(self, task_repository, mock_session):
        """Test getting multiple tasks."""
        task_models = [
            TaskModel(name="task1", dependencies=[], status="pending"),
            TaskModel(name="task2", dependencies=["task1"], status="completed"),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = task_models
        mock_session.execute.return_value = mock_result

        result = await task_repository.get_tasks(["task1", "task2"])

        assert len(result) == 2
        assert "task1" in result
        assert "task2" in result
        assert result["task1"].name == "task1"
        assert result["task2"].dependencies == {"task1"}

    @pytest.mark.asyncio
    async def test_get_tasks_empty_list(self, task_repository):
        """Test getting tasks with empty list."""
        result = await task_repository.get_tasks([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_all_tasks(self, task_repository, mock_session):
        """Test getting all tasks."""
        task_models = [
            TaskModel(name="task1", dependencies=[], status="pending"),
            TaskModel(name="task2", dependencies=["task1"], status="completed"),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = task_models
        mock_session.execute.return_value = mock_result

        result = await task_repository.get_all_tasks()

        assert len(result) == 2
        assert "task1" in result
        assert "task2" in result

    @pytest.mark.asyncio
    async def test_save_new_task(self, task_repository, mock_session, sample_task):
        """Test saving new task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        await task_repository.save_task(sample_task)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_existing_task(self, task_repository, mock_session, sample_task, sample_task_model):
        """Test updating existing task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task_model
        mock_session.execute.return_value = mock_result

        await task_repository.save_task(sample_task)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_tasks_multiple(self, task_repository, mock_session):
        """Test saving multiple tasks."""
        tasks = [
            Task(name="task1", dependencies=set()),
            Task(name="task2", dependencies={"task1"}),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await task_repository.save_tasks(tasks)

        assert mock_session.add.call_count == 2
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_tasks_empty_list(self, task_repository):
        """Test saving empty task list."""
        await task_repository.save_tasks([])

    @pytest.mark.asyncio
    async def test_delete_task_success(self, task_repository, mock_session):
        """Test successful task deletion."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await task_repository.delete_task("test_task")

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, task_repository, mock_session):
        """Test deleting non-existent task."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await task_repository.delete_task("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_task_exists_true(self, task_repository, mock_session):
        """Test task exists check - positive case."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "test_task"
        mock_session.execute.return_value = mock_result

        result = await task_repository.task_exists("test_task")

        assert result is True

    @pytest.mark.asyncio
    async def test_task_exists_false(self, task_repository, mock_session):
        """Test task exists check - negative case."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await task_repository.task_exists("nonexistent")

        assert result is False

    def test_model_to_entity_conversion(self, task_repository):
        """Test conversion from model to entity."""
        model = TaskModel(
            name="test_task",
            dependencies=["dep1", "dep2"],
            status="completed",
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 2),
            error_message="test error",
        )

        entity = task_repository._model_to_entity(model)

        assert entity.name == "test_task"
        assert entity.dependencies == {"dep1", "dep2"}
        assert entity.status == TaskStatus.COMPLETED
        assert entity.error_message == "test error"

    def test_model_to_entity_string_dependencies(self, task_repository):
        """Test conversion with string dependencies (SQLite fallback)."""
        model = TaskModel(
            name="test_task",
            dependencies="dep1,dep2",
            status="pending",
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 1),
        )

        entity = task_repository._model_to_entity(model)

        assert entity.dependencies == {"dep1", "dep2"}

    def test_update_model_from_entity(self, task_repository, sample_task):
        """Test updating model from entity."""
        model = TaskModel(name="test_task")

        task_repository._update_model_from_entity(model, sample_task)

        assert set(model.dependencies) == {"dep1", "dep2"}
        assert model.status == "pending"
        assert model.error_message is None