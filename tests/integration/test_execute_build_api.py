"""Integration tests for execute_build API endpoint (TZ compliance)."""

from unittest.mock import AsyncMock, patch

from app.core.domain.entities import SortedTaskList
from app.core.exceptions import BuildNotFoundException, CircularDependencyException


class TestExecuteBuildAPI:
    """Test execute_build API endpoint according to technical requirements."""
    
    def test_execute_build_success(self, client, override_build_dependency, disable_auth):
        """Test successful build execution start."""
        sort_result = SortedTaskList(
            build_name="make_tests",
            tasks=["compile_exe", "pack_build"],
            algorithm_used="kahns_algorithm",
            execution_time_ms=0.5
        )
        
        override_build_dependency.get_topological_sort.return_value = sort_result
        
        response = client.post(
            "/api/v1/execute_build",
            json={"build": "make_tests"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["build_name"] == "make_tests"
        assert data["status"] == "running"
        assert data["message"] == "Build execution started successfully"
        
        override_build_dependency.get_topological_sort.assert_called_once_with("make_tests")
    
    def test_execute_build_not_found(self, client, override_build_dependency, disable_auth):
        """Test error when build doesn't exist."""
        override_build_dependency.get_topological_sort.side_effect = BuildNotFoundException("Build not found")
        
        response = client.post(
            "/api/v1/execute_build",
            json={"build": "nonexistent_build"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Build 'nonexistent_build' not found" in data["detail"]
    
    def test_execute_build_circular_dependency(self, client, override_build_dependency, disable_auth):
        """Test error when circular dependency is detected."""
        override_build_dependency.get_topological_sort.side_effect = CircularDependencyException(
            ["task1", "task2", "task3"]
        )
        
        response = client.post(
            "/api/v1/execute_build",
            json={"build": "cyclic_build"}
        )
        
        assert response.status_code == 409
        data = response.json()
        assert "Circular dependency detected" in data["detail"]
    
    @patch('app.api.v1.endpoints.execute_build.routes.get_build_service')
    def test_execute_build_empty_build_name(self, mock_get_service, client, disable_auth):
        """Test error when build name is empty."""
        # Mock service to prevent real DB calls
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/execute_build",
            json={"build": ""}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        
        # Service should not be called for validation errors
        mock_service.get_topological_sort.assert_not_called()
    
    @patch('app.api.v1.endpoints.execute_build.routes.get_build_service')
    def test_execute_build_missing_build_field(self, mock_get_service, client, disable_auth):
        """Test error when build field is missing."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/execute_build",
            json={}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        
        # Service should not be called for validation errors
        mock_service.get_topological_sort.assert_not_called()
    
    def test_execute_build_internal_error(self, client, override_build_dependency, disable_auth):
        """Test internal server error handling."""
        override_build_dependency.get_topological_sort.side_effect = Exception("Database error")
        
        response = client.post(
            "/api/v1/execute_build",
            json={"build": "test_build"}
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to execute build" in data["detail"]
    
    def test_execute_build_wrong_method(self, client, disable_auth):
        """Test that GET method is not allowed."""
        response = client.get(
            "/api/v1/execute_build",
            params={"build": "test_build"}
        )
        
        assert response.status_code == 405  # Method Not Allowed