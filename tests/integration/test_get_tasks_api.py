"""Integration tests for get_tasks API endpoint (TZ compliance)."""


from app.core.domain.entities import Build, SortedTaskList
from app.core.domain.enums import BuildStatus
from app.core.exceptions import BuildNotFoundException, CircularDependencyException


class TestGetTasksAPI:
    """Test get_tasks API endpoint according to technical requirements."""
    
    def test_get_tasks_success(self, client, override_build_dependency):
        """Test successful retrieval of sorted tasks."""
        # Setup mock - create a build with tasks
        build = Build(
            name="make_tests",
            tasks=["compile_exe", "pack_build", "run_tests"],
            status=BuildStatus.PENDING,
        )
        
        # Mock the topological sort result
        sort_result = SortedTaskList(
            build_name="make_tests",
            tasks=["compile_exe", "pack_build", "run_tests"],
            algorithm_used="kahns_algorithm",
            execution_time_ms=0.5
        )
        
        override_build_dependency.get_topological_sort.return_value = sort_result
        
        # Make request according to TZ format
        response = client.post(
            "/api/v1/get_tasks",
            json={"build": "make_tests"}
        )
        
        # Verify response matches TZ requirements
        assert response.status_code == 200
        data = response.json()
        
        # Response should be a simple list of task names
        assert isinstance(data, list)
        assert data == ["compile_exe", "pack_build", "run_tests"]
        
        # Verify service was called
        override_build_dependency.get_topological_sort.assert_called_once_with("make_tests")
    
    def test_get_tasks_build_not_found(self, client, override_build_dependency):
        """Test error when build doesn't exist."""
        # Setup mock to raise BuildNotFoundException
        override_build_dependency.get_topological_sort.side_effect = BuildNotFoundException("Build not found")
        
        # Make request
        response = client.post(
            "/api/v1/get_tasks",
            json={"build": "nonexistent_build"}
        )
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "Build 'nonexistent_build' not found" in data["detail"]
    
    def test_get_tasks_circular_dependency(self, client, override_build_dependency):
        """Test error when circular dependency is detected."""
        # Setup mock to raise CircularDependencyException
        override_build_dependency.get_topological_sort.side_effect = CircularDependencyException(
            ["task1", "task2", "task3"]
        )
        
        # Make request
        response = client.post(
            "/api/v1/get_tasks",
            json={"build": "cyclic_build"}
        )
        
        # Verify response
        assert response.status_code == 409
        data = response.json()
        assert "Circular dependency detected" in data["detail"]
    
    def test_get_tasks_empty_build_name(self, client):
        """Test error when build name is empty."""
        # Make request with empty build name
        response = client.post(
            "/api/v1/get_tasks",
            json={"build": ""}
        )
        
        # Verify response
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_get_tasks_missing_build_field(self, client):
        """Test error when build field is missing."""
        # Make request without build field
        response = client.post(
            "/api/v1/get_tasks",
            json={}
        )
        
        # Verify response
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_get_tasks_with_dependencies(self, client, override_build_dependency):
        """Test tasks with complex dependencies."""
        # Setup mock with dependent tasks
        sort_result = SortedTaskList(
            build_name="complex_build",
            tasks=["setup", "compile", "test", "package", "deploy"],
            algorithm_used="kahns_algorithm",
            execution_time_ms=1.2
        )
        
        override_build_dependency.get_topological_sort.return_value = sort_result
        
        # Make request
        response = client.post(
            "/api/v1/get_tasks",
            json={"build": "complex_build"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data == ["setup", "compile", "test", "package", "deploy"]
    
    def test_get_tasks_no_tasks(self, client, override_build_dependency):
        """Test build with no tasks."""
        # Setup mock with empty task list
        sort_result = SortedTaskList(
            build_name="empty_build",
            tasks=[],
            algorithm_used="kahns_algorithm",
            execution_time_ms=0.1
        )
        
        override_build_dependency.get_topological_sort.return_value = sort_result
        
        # Make request
        response = client.post(
            "/api/v1/get_tasks",
            json={"build": "empty_build"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_get_tasks_internal_error(self, client, override_build_dependency):
        """Test internal server error handling."""
        # Setup mock to raise generic exception
        override_build_dependency.get_topological_sort.side_effect = Exception("Database error")
        
        # Make request
        response = client.post(
            "/api/v1/get_tasks",
            json={"build": "test_build"}
        )
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get tasks for build" in data["detail"]
    
    def test_get_tasks_invalid_json(self, client):
        """Test error when request body is not valid JSON."""
        # Make request with invalid JSON
        response = client.post(
            "/api/v1/get_tasks",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Verify response
        assert response.status_code == 422
    
    def test_get_tasks_wrong_method(self, client):
        """Test that GET method is not allowed."""
        # Try GET request (should fail)
        response = client.get(
            "/api/v1/get_tasks",
            params={"build": "test_build"}
        )
        
        # Verify response
        assert response.status_code == 405  # Method Not Allowed