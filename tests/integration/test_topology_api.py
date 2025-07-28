"""Integration tests for topology API."""

from app.core.domain.entities import Build, Task
from app.core.domain.enums import BuildStatus, TaskStatus
from app.core.exceptions import BuildNotFoundException, CircularDependencyException


class TestTopologyAPI:
    """Test topology API endpoints."""
    
    def test_sort_build_tasks_success(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test successful topological sort of build tasks."""
        # Setup mocks
        build = Build(
            name="test_build",
            tasks=["task1", "task2", "task3"],
            status=BuildStatus.PENDING,
        )
        
        # Create tasks with dependencies
        tasks = {
            "task1": Task(name="task1", dependencies=set(), status=TaskStatus.PENDING),
            "task2": Task(name="task2", dependencies={"task1"}, status=TaskStatus.PENDING),
            "task3": Task(name="task3", dependencies={"task1", "task2"}, status=TaskStatus.PENDING),
        }
        
        # Mock the sort result
        from app.core.domain.entities import SortedTaskList
        sort_result = SortedTaskList(
            build_name="test_build",
            tasks=["task1", "task2", "task3"],
            algorithm_used="kahns_algorithm",
            execution_time_ms=0.5
        )
        
        override_build_dependency.get_topological_sort.return_value = sort_result
        
        # Make request
        response = client.get("/api/v1/topology/sort/test_build", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["build_name"] == "test_build"
        assert data["sorted_tasks"] == ["task1", "task2", "task3"]
        assert data["algorithm_used"] == "kahns_algorithm"
        assert data["total_tasks"] == 3
        assert data["has_cycles"] is False
        assert data["cycles"] == []
        
        # Verify service was called
        override_build_dependency.get_topological_sort.assert_called_once_with("test_build")
    
    def test_sort_build_tasks_not_found(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test sorting tasks for non-existent build."""
        # Setup mock to raise BuildNotFoundException
        override_build_dependency.get_topological_sort.side_effect = BuildNotFoundException("Build not found")
        
        # Make request
        response = client.get("/api/v1/topology/sort/nonexistent", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_sort_build_tasks_cycle_detected(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test sorting tasks when circular dependency is detected."""
        # Setup mock to raise CircularDependencyException
        override_build_dependency.get_topological_sort.side_effect = CircularDependencyException(["task1", "task2"])
        
        # Make request
        response = client.get("/api/v1/topology/sort/cyclic_build", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 409
        data = response.json()
        assert "Cyclic dependency detected" in data["detail"]
    
    def test_sort_build_tasks_no_auth(self, client):
        """Test sorting tasks without authentication."""
        response = client.get("/api/v1/topology/sort/test_build")
        
        assert response.status_code == 403
    
    def test_detect_cycles_no_cycles(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test cycle detection when no cycles exist."""
        # Setup mock
        override_build_dependency.detect_cycles.return_value = []
        
        # Make request
        response = client.get("/api/v1/topology/detect-cycles/test_build", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["build_name"] == "test_build"
        assert data["has_cycles"] is False
        assert data["cycles"] == []
        assert data["total_cycles"] == 0
        assert data["analysis_method"] == "depth_first_search"
        
        # Verify service was called
        override_build_dependency.detect_cycles.assert_called_once_with("test_build")
    
    def test_detect_cycles_with_cycles(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test cycle detection when cycles exist."""
        # Setup mock
        cycles = [["task1", "task2", "task3", "task1"], ["task4", "task5", "task4"]]
        override_build_dependency.detect_cycles.return_value = cycles
        
        # Make request
        response = client.get("/api/v1/topology/detect-cycles/cyclic_build", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["build_name"] == "cyclic_build"
        assert data["has_cycles"] is True
        assert data["cycles"] == cycles
        assert data["total_cycles"] == 2
        assert data["analysis_method"] == "depth_first_search"
    
    def test_detect_cycles_build_not_found(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test cycle detection for non-existent build."""
        # Setup mock to raise BuildNotFoundException
        override_build_dependency.detect_cycles.side_effect = BuildNotFoundException("Build not found")
        
        # Make request
        response = client.get("/api/v1/topology/detect-cycles/nonexistent", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_detect_cycles_no_auth(self, client):
        """Test cycle detection without authentication."""
        response = client.get("/api/v1/topology/detect-cycles/test_build")
        
        assert response.status_code == 403
    
    def test_validate_build_dependencies_valid(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test validation of valid build dependencies."""
        # Setup mocks
        build = Build(
            name="test_build",
            tasks=["task1", "task2", "task3"],
            status=BuildStatus.PENDING,
        )
        
        override_build_dependency.get_build.return_value = build
        override_build_dependency.detect_cycles.return_value = []
        
        # Mock task repository to return all tasks
        tasks = {
            "task1": Task(name="task1", dependencies=set(), status=TaskStatus.PENDING),
            "task2": Task(name="task2", dependencies={"task1"}, status=TaskStatus.PENDING),
            "task3": Task(name="task3", dependencies={"task2"}, status=TaskStatus.PENDING),
        }
        
        override_build_dependency._task_repository.get_task.side_effect = lambda name: tasks.get(name)
        
        # Mock topological sort result
        from app.core.domain.entities import SortedTaskList
        sort_result = SortedTaskList(
            build_name="test_build",
            tasks=["task1", "task2", "task3"],
            algorithm_used="kahns_algorithm",
            execution_time_ms=0.5
        )
        override_build_dependency.get_topological_sort.return_value = sort_result
        
        # Make request
        response = client.get("/api/v1/topology/validate/test_build", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["build_name"] == "test_build"
        assert data["is_valid"] is True
        assert data["has_cycles"] is False
        assert data["cycles"] == []
        assert data["missing_tasks"] == []
        assert data["total_tasks"] == 3
        assert data["sort_possible"] is True
        assert data["suggested_order"] == ["task1", "task2", "task3"]
        
        # Verify service was called
        override_build_dependency.get_build.assert_called_once_with("test_build")
        override_build_dependency.detect_cycles.assert_called_once_with("test_build")
    
    def test_validate_build_dependencies_with_cycles(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test validation when build has circular dependencies."""
        # Setup mocks
        build = Build(
            name="cyclic_build",
            tasks=["task1", "task2"],
            status=BuildStatus.PENDING,
        )
        
        override_build_dependency.get_build.return_value = build
        override_build_dependency.detect_cycles.return_value = [["task1", "task2", "task1"]]
        
        # Mock task repository
        tasks = {
            "task1": Task(name="task1", dependencies={"task2"}, status=TaskStatus.PENDING),
            "task2": Task(name="task2", dependencies={"task1"}, status=TaskStatus.PENDING),
        }
        
        override_build_dependency._task_repository.get_task.side_effect = lambda name: tasks.get(name)
        
        # Make request
        response = client.get("/api/v1/topology/validate/cyclic_build", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["build_name"] == "cyclic_build"
        assert data["is_valid"] is False
        assert data["has_cycles"] is True
        assert data["cycles"] == [["task1", "task2", "task1"]]
        assert data["missing_tasks"] == []
        assert data["total_tasks"] == 2
        assert data["sort_possible"] is False
        assert data["suggested_order"] == []
    
    def test_validate_build_dependencies_missing_tasks(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test validation when build references missing tasks."""
        # Setup mocks
        build = Build(
            name="incomplete_build",
            tasks=["task1", "task2", "missing_task"],
            status=BuildStatus.PENDING,
        )
        
        override_build_dependency.get_build.return_value = build
        override_build_dependency.detect_cycles.return_value = []
        
        # Mock task repository - missing_task doesn't exist
        tasks = {
            "task1": Task(name="task1", dependencies=set(), status=TaskStatus.PENDING),
            "task2": Task(name="task2", dependencies={"task1"}, status=TaskStatus.PENDING),
        }
        
        override_build_dependency._task_repository.get_task.side_effect = lambda name: tasks.get(name)
        
        # Make request
        response = client.get("/api/v1/topology/validate/incomplete_build", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["build_name"] == "incomplete_build"
        assert data["is_valid"] is False
        assert data["has_cycles"] is False
        assert data["cycles"] == []
        assert data["missing_tasks"] == ["missing_task"]
        assert data["total_tasks"] == 3
        assert data["sort_possible"] is False
        assert data["suggested_order"] == []
    
    def test_validate_build_dependencies_not_found(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test validation for non-existent build."""
        # Setup mock to return None
        override_build_dependency.get_build.return_value = None
        
        # Make request
        response = client.get("/api/v1/topology/validate/nonexistent", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_validate_build_dependencies_no_auth(self, client):
        """Test validation without authentication."""
        response = client.get("/api/v1/topology/validate/test_build")
        
        assert response.status_code == 403