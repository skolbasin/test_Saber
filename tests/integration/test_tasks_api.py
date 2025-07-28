"""Integration tests for tasks API."""

from app.core.domain.enums import TaskStatus


class TestTasksAPI:
    """Test tasks API endpoints."""
    
    def test_create_task_success(self, client, override_build_dependency, override_current_user, auth_headers, mock_task):
        """Test successful task creation."""
        # Setup mocks
        override_build_dependency._task_repository.get_task.return_value = None  # Task doesn't exist
        override_build_dependency._task_repository.save_task.return_value = mock_task
        
        # Make request
        response = client.post(
            "/api/v1/tasks",
            json={
                "name": "test_task",
                "dependencies": []
            },
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_task"
        assert data["dependencies"] == []
        assert data["status"] == "pending"
        
        # Verify service was called
        override_build_dependency._task_repository.get_task.assert_called_once_with("test_task")
        override_build_dependency._task_repository.save_task.assert_called_once()
    
    def test_create_task_already_exists(self, client, override_build_dependency, override_current_user, auth_headers, mock_task):
        """Test creating task that already exists."""
        # Setup mock - task already exists
        override_build_dependency._task_repository.get_task.return_value = mock_task
        
        # Make request
        response = client.post(
            "/api/v1/tasks",
            json={
                "name": "test_task",
                "dependencies": []
            },
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]
    
    def test_create_task_no_auth(self, client):
        """Test creating task without authentication."""
        response = client.post(
            "/api/v1/tasks",
            json={
                "name": "test_task",
                "dependencies": []
            }
        )
        
        assert response.status_code == 403
    
    def test_create_task_invalid_data(self, client, override_current_user, auth_headers):
        """Test creating task with invalid data."""
        response = client.post(
            "/api/v1/tasks",
            json={
                "name": "",  # Empty name
                "dependencies": ["self"]  # Invalid dependency
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_get_task_success(self, client, override_build_dependency, override_current_user, auth_headers, mock_task):
        """Test successful task retrieval."""
        # Setup mock
        override_build_dependency._task_repository.get_task.return_value = mock_task
        
        # Make request
        response = client.get("/api/v1/tasks/test_task", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_task"
        assert data["status"] == "pending"
        assert data["dependencies"] == []
        
        # Verify service was called
        override_build_dependency._task_repository.get_task.assert_called_with("test_task")
    
    def test_get_task_not_found(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test getting non-existent task."""
        # Setup mock to return None
        override_build_dependency._task_repository.get_task.return_value = None
        
        # Make request
        response = client.get("/api/v1/tasks/nonexistent", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_get_task_no_auth(self, client):
        """Test getting task without authentication."""
        response = client.get("/api/v1/tasks/test_task")
        
        assert response.status_code == 403
    
    def test_list_tasks_success(self, client, override_build_dependency, override_current_user, auth_headers, mock_task):
        """Test listing tasks."""
        # Setup mock
        override_build_dependency._task_repository.get_all_tasks.return_value = {"test_task": mock_task}
        
        # Make request
        response = client.get("/api/v1/tasks", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["name"] == "test_task"
        
        # Verify service was called
        override_build_dependency._task_repository.get_all_tasks.assert_called_once()
    
    def test_list_tasks_empty(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test listing tasks when none exist."""
        # Setup mock
        override_build_dependency._task_repository.get_all_tasks.return_value = {}
        
        # Make request
        response = client.get("/api/v1/tasks", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["tasks"]) == 0
    
    def test_list_tasks_with_pagination(self, client, override_build_dependency, override_current_user, auth_headers, mock_task):
        """Test listing tasks with pagination."""
        # Setup mock - create multiple tasks
        from app.core.domain.entities import Task
        tasks = {
            f"task_{i}": Task(
                name=f"task_{i}",
                dependencies=set(),
                status=TaskStatus.PENDING
            ) 
            for i in range(20)
        }
        override_build_dependency._task_repository.get_all_tasks.return_value = tasks
        
        # Make request with pagination
        response = client.get(
            "/api/v1/tasks?limit=5&offset=10",
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 20
        assert len(data["tasks"]) == 5  # Limited to 5
        
        # Verify service was called
        override_build_dependency._task_repository.get_all_tasks.assert_called_once()
    
    def test_list_tasks_no_auth(self, client):
        """Test listing tasks without authentication."""
        response = client.get("/api/v1/tasks")
        
        assert response.status_code == 403
    
    def test_update_task_success(self, client, override_build_dependency, override_current_user, auth_headers, mock_task):
        """Test successful task update."""
        # Setup mock - task exists
        override_build_dependency._task_repository.get_task.return_value = mock_task
        
        # Create updated task
        from app.core.domain.entities import Task
        updated_task = Task(
            name="test_task",
            dependencies={"dep1", "dep2"},
            status=TaskStatus.RUNNING
        )
        override_build_dependency._task_repository.save_task.return_value = updated_task
        
        # Make request
        response = client.put(
            "/api/v1/tasks/test_task",
            json={
                "dependencies": ["dep1", "dep2"],
                "status": "running"
            },
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        # Sort dependencies since sets don't guarantee order
        assert sorted(data["dependencies"]) == ["dep1", "dep2"]
        assert data["status"] == "running"
        
        # Verify service was called
        override_build_dependency._task_repository.get_task.assert_called_with("test_task")
        override_build_dependency._task_repository.save_task.assert_called_once()
    
    def test_update_task_not_found(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test updating non-existent task."""
        # Setup mock - task doesn't exist
        override_build_dependency._task_repository.get_task.return_value = None
        
        # Make request
        response = client.put(
            "/api/v1/tasks/nonexistent",
            json={
                "status": "completed"
            },
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_update_task_no_auth(self, client):
        """Test updating task without authentication."""
        response = client.put(
            "/api/v1/tasks/test_task",
            json={
                "status": "completed"
            }
        )
        
        assert response.status_code == 403
    
    def test_delete_task_success(self, client, override_build_dependency, override_current_user, auth_headers, mock_task):
        """Test successful task deletion."""
        # Setup mock
        override_build_dependency._task_repository.get_task.return_value = mock_task
        override_build_dependency._task_repository.delete_task.return_value = True
        
        # Make request
        response = client.delete("/api/v1/tasks/test_task", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify service was called
        override_build_dependency._task_repository.get_task.assert_called_with("test_task")
        override_build_dependency._task_repository.delete_task.assert_called_once_with("test_task")
    
    def test_delete_task_not_found(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test deleting non-existent task."""
        # Setup mock - task doesn't exist
        override_build_dependency._task_repository.get_task.return_value = None
        
        # Make request
        response = client.delete("/api/v1/tasks/nonexistent", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_delete_task_no_auth(self, client):
        """Test deleting task without authentication."""
        response = client.delete("/api/v1/tasks/test_task")
        
        assert response.status_code == 403