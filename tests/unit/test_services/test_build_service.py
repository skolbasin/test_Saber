"""Tests for build service implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.domain.entities import Build, Task, SortedTaskList
from app.core.domain.enums import BuildStatus, TaskStatus, SortAlgorithm
from app.core.exceptions import (
    BuildNotFoundException,
    TaskNotFoundException,
    CircularDependencyException,
)
from app.core.services.build_service import BuildService


@pytest.fixture
def mock_build_repository():
    """Create mock build repository."""
    return AsyncMock()


@pytest.fixture
def mock_task_repository():
    """Create mock task repository."""
    return AsyncMock()


@pytest.fixture
def mock_topology_service():
    """Create mock topology service."""
    return MagicMock()


@pytest.fixture
def build_service(mock_build_repository, mock_task_repository, mock_topology_service):
    """Create build service with mocked dependencies."""
    return BuildService(
        mock_build_repository,
        mock_task_repository,
        mock_topology_service,
    )


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    return {
        "task_a": Task(name="task_a", dependencies=set()),
        "task_b": Task(name="task_b", dependencies={"task_a"}),
        "task_c": Task(name="task_c", dependencies={"task_b"}),
    }


@pytest.fixture
def sample_build():
    """Create sample build for testing."""
    return Build(
        name="test_build",
        tasks=["task_a", "task_b", "task_c"],
        status=BuildStatus.PENDING,
    )


@pytest.fixture
def sample_sorted_tasks():
    """Create sample sorted task list."""
    return SortedTaskList(
        build_name="test_build",
        tasks=["task_a", "task_b", "task_c"],
        algorithm_used="kahn",
        execution_time_ms=5.0,
        has_cycles=False,
    )


class TestBuildService:
    """Test cases for BuildService."""

    @pytest.mark.asyncio
    async def test_get_build_found(self, build_service, mock_build_repository, sample_build):
        """Test getting existing build."""
        mock_build_repository.get_build.return_value = sample_build
        
        result = await build_service.get_build("test_build")
        
        assert result == sample_build
        mock_build_repository.get_build.assert_called_once_with("test_build")

    @pytest.mark.asyncio
    async def test_get_build_not_found(self, build_service, mock_build_repository):
        """Test getting non-existent build."""
        mock_build_repository.get_build.return_value = None
        
        result = await build_service.get_build("nonexistent")
        
        assert result is None
        mock_build_repository.get_build.assert_called_once_with("nonexistent")

    @pytest.mark.asyncio
    async def test_get_builds_multiple(self, build_service, mock_build_repository):
        """Test getting multiple builds."""
        builds = {
            "build1": Build(name="build1", tasks=["task1"]),
            "build2": Build(name="build2", tasks=["task2"]),
        }
        mock_build_repository.get_builds.return_value = builds
        
        result = await build_service.get_builds(["build1", "build2"])
        
        assert result == builds
        mock_build_repository.get_builds.assert_called_once_with(["build1", "build2"])

    @pytest.mark.asyncio
    async def test_get_builds_empty_list(self, build_service):
        """Test getting builds with empty list."""
        result = await build_service.get_builds([])
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_all_builds(self, build_service, mock_build_repository):
        """Test getting all builds."""
        builds = {
            "build1": Build(name="build1", tasks=["task1"]),
            "build2": Build(name="build2", tasks=["task2"]),
        }
        mock_build_repository.get_all_builds.return_value = builds
        
        result = await build_service.get_all_builds()
        
        assert result == builds
        mock_build_repository.get_all_builds.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_build_success(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        mock_topology_service,
        sample_build,
        sample_tasks,
    ):
        """Test successful build creation."""
        mock_task_repository.get_tasks.return_value = sample_tasks
        mock_topology_service.detect_cycles.return_value = []
        mock_topology_service.validate_dependencies.return_value = []
        mock_build_repository.save_build.return_value = sample_build
        
        result = await build_service.create_build(sample_build)
        
        assert result == sample_build
        mock_task_repository.get_tasks.assert_called_once_with(sample_build.tasks)
        mock_topology_service.detect_cycles.assert_called_once_with(sample_tasks)
        mock_topology_service.validate_dependencies.assert_called_once_with(
            sample_build, sample_tasks
        )
        mock_build_repository.save_build.assert_called_once_with(sample_build)

    @pytest.mark.asyncio
    async def test_create_build_missing_tasks(
        self,
        build_service,
        mock_task_repository,
        sample_build,
    ):
        """Test build creation with missing tasks."""
        mock_task_repository.get_tasks.return_value = {"task_a": Task(name="task_a", dependencies=set())}
        
        with pytest.raises(TaskNotFoundException, match="Missing tasks:"):
            await build_service.create_build(sample_build)

    @pytest.mark.asyncio
    async def test_create_build_circular_dependencies(
        self,
        build_service,
        mock_task_repository,
        mock_topology_service,
        sample_build,
        sample_tasks,
    ):
        """Test build creation with circular dependencies."""
        mock_task_repository.get_tasks.return_value = sample_tasks
        mock_topology_service.detect_cycles.return_value = [["task_a", "task_b", "task_a"]]
        
        with pytest.raises(CircularDependencyException):
            await build_service.create_build(sample_build)

    @pytest.mark.asyncio
    async def test_create_build_missing_dependencies(
        self,
        build_service,
        mock_task_repository,
        mock_topology_service,
        sample_build,
        sample_tasks,
    ):
        """Test build creation with missing dependencies."""
        mock_task_repository.get_tasks.return_value = sample_tasks
        mock_topology_service.detect_cycles.return_value = []
        mock_topology_service.validate_dependencies.return_value = ["missing_dep"]
        
        with pytest.raises(TaskNotFoundException, match="Missing dependencies: missing_dep"):
            await build_service.create_build(sample_build)

    @pytest.mark.asyncio
    async def test_update_build_success(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        mock_topology_service,
        sample_build,
        sample_tasks,
    ):
        """Test successful build update."""
        mock_build_repository.get_build.return_value = sample_build
        mock_task_repository.get_tasks.return_value = sample_tasks
        mock_topology_service.detect_cycles.return_value = []
        mock_topology_service.validate_dependencies.return_value = []
        mock_build_repository.save_build.return_value = sample_build
        
        result = await build_service.update_build(sample_build)
        
        assert result == sample_build
        mock_build_repository.get_build.assert_called_once_with(sample_build.name)

    @pytest.mark.asyncio
    async def test_update_build_not_found(
        self,
        build_service,
        mock_build_repository,
        sample_build,
    ):
        """Test updating non-existent build."""
        mock_build_repository.get_build.return_value = None
        
        with pytest.raises(BuildNotFoundException, match="Build 'test_build' not found"):
            await build_service.update_build(sample_build)

    @pytest.mark.asyncio
    async def test_delete_build_success(self, build_service, mock_build_repository):
        """Test successful build deletion."""
        mock_build_repository.delete_build.return_value = True
        
        result = await build_service.delete_build("test_build")
        
        assert result is True
        mock_build_repository.delete_build.assert_called_once_with("test_build")

    @pytest.mark.asyncio
    async def test_delete_build_not_found(self, build_service, mock_build_repository):
        """Test deleting non-existent build."""
        mock_build_repository.delete_build.return_value = False
        
        result = await build_service.delete_build("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_sorted_tasks_success(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        mock_topology_service,
        sample_build,
        sample_tasks,
        sample_sorted_tasks,
    ):
        """Test getting sorted tasks for build."""
        mock_build_repository.get_build.return_value = sample_build
        mock_task_repository.get_tasks.return_value = sample_tasks
        mock_topology_service.sort_tasks = AsyncMock(return_value=sample_sorted_tasks)
        
        result = await build_service.get_sorted_tasks("test_build")
        
        assert result == sample_sorted_tasks
        mock_build_repository.get_build.assert_called_once_with("test_build")
        mock_task_repository.get_tasks.assert_called_once_with(sample_build.tasks)
        mock_topology_service.sort_tasks.assert_called_once_with(
            sample_build, sample_tasks, SortAlgorithm.KAHN
        )

    @pytest.mark.asyncio
    async def test_get_sorted_tasks_build_not_found(
        self,
        build_service,
        mock_build_repository,
    ):
        """Test getting sorted tasks for non-existent build."""
        mock_build_repository.get_build.return_value = None
        
        with pytest.raises(BuildNotFoundException, match="Build 'nonexistent' not found"):
            await build_service.get_sorted_tasks("nonexistent")

    @pytest.mark.asyncio
    async def test_get_sorted_tasks_missing_tasks(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        sample_build,
    ):
        """Test getting sorted tasks with missing tasks."""
        mock_build_repository.get_build.return_value = sample_build
        mock_task_repository.get_tasks.return_value = {"task_a": Task(name="task_a", dependencies=set())}
        
        with pytest.raises(TaskNotFoundException, match="Missing tasks:"):
            await build_service.get_sorted_tasks("test_build")

    @pytest.mark.asyncio
    async def test_execute_build_success(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        mock_topology_service,
        sample_build,
        sample_tasks,
        sample_sorted_tasks,
    ):
        """Test successful build execution."""
        mock_build_repository.get_build.return_value = sample_build
        mock_task_repository.get_tasks.return_value = sample_tasks
        mock_topology_service.sort_tasks = AsyncMock(return_value=sample_sorted_tasks)
        mock_topology_service.validate_dependencies.return_value = []
        
        completed_build = Build(
            name=sample_build.name,
            tasks=sample_build.tasks,
            status=BuildStatus.COMPLETED,
            created_at=sample_build.created_at,
        )
        mock_build_repository.save_build.return_value = completed_build
        
        result = await build_service.execute_build("test_build")
        
        assert result.status == BuildStatus.COMPLETED
        
        # Verify build status updates
        save_calls = mock_build_repository.save_build.call_args_list
        assert len(save_calls) == 2  # Running and Completed states
        
        running_build = save_calls[0][0][0]
        assert running_build.status == BuildStatus.RUNNING
        
        completed_build = save_calls[1][0][0]
        assert completed_build.status == BuildStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_build_not_found(
        self,
        build_service,
        mock_build_repository,
    ):
        """Test executing non-existent build."""
        mock_build_repository.get_build.return_value = None
        
        with pytest.raises(BuildNotFoundException, match="Build 'nonexistent' not found"):
            await build_service.execute_build("nonexistent")

    @pytest.mark.asyncio
    async def test_execute_build_failure(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        mock_topology_service,
        sample_build,
    ):
        """Test build execution failure."""
        mock_build_repository.get_build.return_value = sample_build
        mock_task_repository.get_tasks.side_effect = Exception("Database error")
        
        failed_build = Build(
            name=sample_build.name,
            tasks=sample_build.tasks,
            status=BuildStatus.FAILED,
            created_at=sample_build.created_at,
        )
        mock_build_repository.save_build.return_value = failed_build
        
        with pytest.raises(Exception, match="Database error"):
            await build_service.execute_build("test_build")
        
        # Verify build was marked as failed
        save_calls = mock_build_repository.save_build.call_args_list
        assert len(save_calls) == 2  # Running and Failed states
        
        failed_build_call = save_calls[1][0][0]
        assert failed_build_call.status == BuildStatus.FAILED

    @pytest.mark.asyncio
    async def test_cancel_build_success(
        self,
        build_service,
        mock_build_repository,
        sample_build,
    ):
        """Test successful build cancellation."""
        mock_build_repository.get_build.return_value = sample_build
        
        cancelled_build = Build(
            name=sample_build.name,
            tasks=sample_build.tasks,
            status=BuildStatus.CANCELLED,
            created_at=sample_build.created_at,
        )
        mock_build_repository.save_build.return_value = cancelled_build
        
        result = await build_service.cancel_build("test_build")
        
        assert result.status == BuildStatus.CANCELLED
        mock_build_repository.get_build.assert_called_once_with("test_build")
        mock_build_repository.save_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_build_not_found(
        self,
        build_service,
        mock_build_repository,
    ):
        """Test cancelling non-existent build."""
        mock_build_repository.get_build.return_value = None
        
        with pytest.raises(BuildNotFoundException, match="Build 'nonexistent' not found"):
            await build_service.cancel_build("nonexistent")

    @pytest.mark.asyncio
    async def test_get_build_execution_status(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        sample_build,
        sample_tasks,
    ):
        """Test getting build execution status."""
        mock_build_repository.get_build.return_value = sample_build
        mock_task_repository.get_tasks.return_value = sample_tasks
        
        result = await build_service.get_build_execution_status("test_build")
        
        expected = {
            "task_a": TaskStatus.PENDING,
            "task_b": TaskStatus.PENDING,
            "task_c": TaskStatus.PENDING,
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_validate_build_dependencies_success(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        mock_topology_service,
        sample_build,
        sample_tasks,
    ):
        """Test successful build dependencies validation."""
        mock_build_repository.get_build.return_value = sample_build
        mock_task_repository.get_tasks.return_value = sample_tasks
        mock_topology_service.validate_dependencies.return_value = []
        mock_topology_service.detect_cycles.return_value = []
        
        is_valid, issues = await build_service.validate_build_dependencies("test_build")
        
        assert is_valid is True
        assert issues == []

    @pytest.mark.asyncio
    async def test_validate_build_dependencies_with_issues(
        self,
        build_service,
        mock_build_repository,
        mock_task_repository,
        mock_topology_service,
        sample_build,
        sample_tasks,
    ):
        """Test build dependencies validation with issues."""
        mock_build_repository.get_build.return_value = sample_build
        mock_task_repository.get_tasks.return_value = sample_tasks
        mock_topology_service.validate_dependencies.return_value = ["missing_dep"]
        mock_topology_service.detect_cycles.return_value = [["task_a", "task_b", "task_a"]]
        
        is_valid, issues = await build_service.validate_build_dependencies("test_build")
        
        assert is_valid is False
        assert "missing_dep" in issues
        assert "Circular dependency: task_a -> task_b -> task_a" in issues

    @pytest.mark.asyncio
    async def test_reload_builds_from_config(self, build_service):
        """Test reloading builds from configuration."""
        result = await build_service.reload_builds_from_config()
        
        # Placeholder implementation returns 0
        assert result == 0