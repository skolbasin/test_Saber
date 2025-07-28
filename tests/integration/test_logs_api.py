"""Integration tests for logs management API endpoints."""

from unittest.mock import Mock, patch


class TestLogsAPI:
    """Test logs management API endpoints."""
    
    @patch('app.api.v1.endpoints.logs.routes.get_log_statistics')
    def test_logs_statistics_success(self, mock_task, authenticated_client):
        """Test successful log statistics retrieval."""
        mock_result = Mock()
        mock_result.result = {
            "task": "get_log_statistics",
            "timestamp": "2025-07-26T12:00:00Z",
            "logs_directory": "/app/logs",
            "total_size_mb": 45.67,
            "files_count": {
                "current_logs": 2,
                "rotated_logs": 5,
                "archives": 10,
                "total": 17
            },
            "current_logs": {
                "saber.log": {
                    "size_bytes": 8388608,
                    "size_mb": 8.0,
                    "modified": "2025-07-26T12:00:00"
                }
            },
            "rotated_logs": {},
            "archives": {}
        }
        
        mock_task.apply.return_value = mock_result
        
        response = authenticated_client.get("/api/v1/logs/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"] == "get_log_statistics"
        assert data["logs_directory"] == "/app/logs"
        assert data["total_size_mb"] == 45.67
        assert "files_count" in data
        assert "current_logs" in data
        
        # Verify mock was called
        mock_task.apply.assert_called_once()
    
    def test_logs_statistics_unauthorized(self, client):
        """Test log statistics without authentication."""
        response = client.get("/api/v1/logs/statistics")
        assert response.status_code in [401, 403]  # Either is valid for unauthorized
    
    @patch('app.api.v1.endpoints.logs.routes.archive_old_logs')
    def test_logs_archive_success(self, mock_task, authenticated_client):
        """Test successful log archiving trigger."""
        mock_celery_task = Mock()
        mock_celery_task.id = "test-task-id-123"
        mock_task.delay.return_value = mock_celery_task
        
        response = authenticated_client.post(
            "/api/v1/logs/archive",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"] == "archive_old_logs"
        assert data["task_id"] == "test-task-id-123"
        assert data["status"] == "started"
        assert data["message"] == "Log archiving task started successfully"
        assert data["archives_created"] == 0
        assert data["total_size_archived_mb"] == 0.0
        
        # Verify mock was called
        mock_task.delay.assert_called_once()
    
    def test_logs_archive_unauthorized(self, client):
        """Test log archiving without authentication."""
        response = client.post("/api/v1/logs/archive", json={})
        assert response.status_code in [401, 403]  # Either is valid for unauthorized
    
    @patch('app.api.v1.endpoints.logs.routes.cleanup_old_archives')
    def test_logs_cleanup_success(self, mock_task, authenticated_client):
        """Test successful log cleanup trigger."""
        mock_celery_task = Mock()
        mock_celery_task.id = "test-cleanup-task-456"
        mock_task.delay.return_value = mock_celery_task
        
        response = authenticated_client.post("/api/v1/logs/cleanup", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"] == "cleanup_old_archives"
        assert data["task_id"] == "test-cleanup-task-456"
        assert data["status"] == "started"
        assert data["message"] == "Archive cleanup task started successfully"
        assert data["retention_days"] == 7
        assert data["archives_cleaned"] == 0
        assert data["space_freed_mb"] == 0.0
        
        # Verify mock was called with default retention
        mock_task.delay.assert_called_once_with(retention_days=7)
    
    @patch('app.api.v1.endpoints.logs.routes.cleanup_old_archives')
    def test_logs_cleanup_custom_retention(self, mock_task, authenticated_client):
        """Test log cleanup with custom retention period."""
        mock_celery_task = Mock()
        mock_celery_task.id = "test-cleanup-task-789"
        mock_task.delay.return_value = mock_celery_task
        
        response = authenticated_client.post(
            "/api/v1/logs/cleanup?retention_days=14",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["retention_days"] == 14
        
        # Verify mock was called with custom retention
        mock_task.delay.assert_called_once_with(retention_days=14)
    
    def test_logs_cleanup_unauthorized(self, client):
        """Test log cleanup without authentication."""
        response = client.post("/api/v1/logs/cleanup", json={})
        assert response.status_code in [401, 403]  # Either is valid for unauthorized
    
    def test_logs_endpoints_wrong_methods(self, authenticated_client):
        """Test that wrong HTTP methods are not allowed."""
        response = authenticated_client.post("/api/v1/logs/statistics", json={})
        assert response.status_code == 405
        
        response = authenticated_client.get("/api/v1/logs/archive")
        assert response.status_code == 405
        
        response = authenticated_client.get("/api/v1/logs/cleanup")
        assert response.status_code == 405
    
    @patch('app.api.v1.endpoints.logs.routes.archive_old_logs')
    def test_logs_archive_invalid_json(self, mock_task, authenticated_client):
        """Test log archiving with invalid JSON."""
        # Mock to prevent actual task execution
        mock_celery_task = Mock()
        mock_celery_task.id = "test-id"
        mock_task.delay.return_value = mock_celery_task
        
        response = authenticated_client.post(
            "/api/v1/logs/archive",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should still work because body is optional for this endpoint
        assert response.status_code in [200, 422]
    
    @patch('app.api.v1.endpoints.logs.routes.cleanup_old_archives')
    def test_logs_cleanup_invalid_retention(self, mock_task, authenticated_client):
        """Test log cleanup with invalid retention period."""
        mock_celery_task = Mock()
        mock_celery_task.id = "test-id"
        mock_task.delay.return_value = mock_celery_task
        
        response = authenticated_client.post(
            "/api/v1/logs/cleanup?retention_days=-1",
            json={}
        )
        
        # Should still work but use the provided value
        assert response.status_code == 200
        data = response.json()
        assert data["retention_days"] == -1
    
    @patch('app.api.v1.endpoints.logs.routes.get_log_statistics')
    def test_logs_statistics_celery_error(self, mock_task, authenticated_client):
        """Test log statistics when Celery task fails."""
        mock_task.apply.side_effect = Exception("Celery error")
        
        # This test verifies that Celery errors propagate correctly
        # In real environment, the exception would be caught by FastAPI
        try:
            response = authenticated_client.get("/api/v1/logs/statistics")
            # If we reach here, check it's a 500 error
            assert response.status_code == 500
        except Exception as e:
            # If exception propagates, that's also expected behavior
            assert "Celery error" in str(e)