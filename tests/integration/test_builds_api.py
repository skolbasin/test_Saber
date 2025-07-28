"""Integration tests for builds API."""


class TestBuildsAPI:
    """Test builds API endpoints."""

    def test_create_build_success(self, client, override_build_dependency, override_current_user, auth_headers,
                                  mock_build):
        """Test successful build creation."""
        # Setup mocks
        override_build_dependency.get_build.return_value = None  # Build doesn't exist
        override_build_dependency.create_build.return_value = mock_build

        # Make request
        response = client.post(
            "/api/v1/builds",
            json={
                "name": "test_build",
                "tasks": ["task1", "task2", "task3"]
            },
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_build"
        assert data["tasks"] == ["task1", "task2", "task3"]
        assert data["status"] == "pending"

        # Verify service was called
        override_build_dependency.get_build.assert_called_once_with("test_build")
        override_build_dependency.create_build.assert_called_once()

    def test_create_build_already_exists(self, client, override_build_dependency, override_current_user, auth_headers,
                                         mock_build):
        """Test creating build that already exists."""
        # Setup mock - build already exists
        override_build_dependency.get_build.return_value = mock_build

        # Make request
        response = client.post(
            "/api/v1/builds",
            json={
                "name": "test_build",
                "tasks": ["task1"]
            },
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]

    def test_create_build_no_auth(self, client):
        """Test creating build without authentication."""
        response = client.post(
            "/api/v1/builds",
            json={
                "name": "test_build",
                "tasks": ["task1"]
            }
        )

        assert response.status_code == 403

    def test_create_build_invalid_data(self, client, override_current_user, auth_headers):
        """Test creating build with invalid data."""
        response = client.post(
            "/api/v1/builds",
            json={
                "name": "",  # Empty name
                "tasks": []  # Empty tasks
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_get_build_success(self, client, override_build_dependency, override_current_user, auth_headers,
                               mock_build):
        """Test successful build retrieval."""
        # Setup mock
        override_build_dependency.get_build.return_value = mock_build

        # Make request
        response = client.get("/api/v1/builds/test_build", headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_build"
        assert data["status"] == "pending"
        assert data["tasks"] == ["task1", "task2", "task3"]

        # Verify service was called
        override_build_dependency.get_build.assert_called_once_with("test_build")

    def test_get_build_not_found(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test getting non-existent build."""
        # Setup mock to return None
        override_build_dependency.get_build.return_value = None

        # Make request
        response = client.get("/api/v1/builds/nonexistent", headers=auth_headers)

        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_get_build_no_auth(self, client):
        """Test getting build without authentication."""
        response = client.get("/api/v1/builds/test_build")

        assert response.status_code == 403

    def test_list_builds_success(self, client, override_build_dependency, override_current_user, auth_headers,
                                 mock_build):
        """Test listing builds."""
        # Setup mock
        override_build_dependency.get_all_builds.return_value = {"test_build": mock_build}

        # Make request
        response = client.get("/api/v1/builds", headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["builds"]) == 1
        assert data["builds"][0]["name"] == "test_build"

        # Verify service was called
        override_build_dependency.get_all_builds.assert_called_once()

    def test_list_builds_empty(self, client, override_build_dependency, override_current_user, auth_headers):
        """Test listing builds when none exist."""
        # Setup mock
        override_build_dependency.get_all_builds.return_value = {}

        # Make request
        response = client.get("/api/v1/builds", headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["builds"]) == 0

    def test_list_builds_with_pagination(self, client, override_build_dependency, override_current_user, auth_headers,
                                         mock_build):
        """Test listing builds with pagination."""
        # Setup mock - create multiple builds
        from app.core.domain.entities import Build
        builds = {
            f"build_{i}": Build(
                name=f"build_{i}",
                tasks=mock_build.tasks,
                status=mock_build.status
            )
            for i in range(20)
        }
        override_build_dependency.get_all_builds.return_value = builds

        # Make request with pagination
        response = client.get(
            "/api/v1/builds?limit=5&offset=10",
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 20
        assert len(data["builds"]) == 5  # Limited to 5

        # Verify service was called
        override_build_dependency.get_all_builds.assert_called_once()

    def test_list_builds_no_auth(self, client):
        """Test listing builds without authentication."""
        response = client.get("/api/v1/builds")

        assert response.status_code == 403
