"""Integration tests for authentication API."""


from app.core.auth.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    InvalidTokenException,
)


class TestAuthAPI:
    """Test authentication API endpoints."""
    
    def test_register_success(self, client, override_auth_dependency, mock_user):
        """Test successful user registration."""
        # Setup mock
        override_auth_dependency.register_user.return_value = mock_user
        
        # Make request
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            }
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert "id" in data
        
        # Verify service was called
        override_auth_dependency.register_user.assert_called_once_with(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
    
    def test_register_user_already_exists(self, client, override_auth_dependency):
        """Test registration with existing username."""
        # Setup mock to raise exception
        override_auth_dependency.register_user.side_effect = UserAlreadyExistsException("testuser")
        
        # Make request
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            }
        )
        
        # Verify response
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "password123",
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_register_short_password(self, client):
        """Test registration with too short password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "123",  # Too short
            }
        )
        
        assert response.status_code == 422
    
    def test_login_success(self, client, override_auth_dependency, mock_token_pair):
        """Test successful login."""
        # Setup mock
        override_auth_dependency.authenticate_user.return_value = mock_token_pair
        
        # Make request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "password123",
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == mock_token_pair.access_token
        assert data["refresh_token"] == mock_token_pair.refresh_token
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800
        
        # Verify service was called
        override_auth_dependency.authenticate_user.assert_called_once_with(
            username="testuser",
            password="password123"
        )
    
    def test_login_invalid_credentials(self, client, override_auth_dependency):
        """Test login with invalid credentials."""
        # Setup mock to raise exception
        override_auth_dependency.authenticate_user.side_effect = InvalidCredentialsException()
        
        # Make request
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword",
            }
        )
        
        # Verify response
        assert response.status_code == 401
        data = response.json()
        assert "Invalid username or password" in data["detail"]
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                # Missing password
            }
        )
        
        assert response.status_code == 422
    
    def test_refresh_token_success(self, client, override_auth_dependency, mock_token_pair):
        """Test successful token refresh."""
        # Setup mock
        override_auth_dependency.refresh_access_token.return_value = mock_token_pair
        
        # Make request
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "valid_refresh_token",
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == mock_token_pair.access_token
        assert data["refresh_token"] == mock_token_pair.refresh_token
        
        # Verify service was called
        override_auth_dependency.refresh_access_token.assert_called_once_with("valid_refresh_token")
    
    def test_refresh_token_invalid(self, client, override_auth_dependency):
        """Test refresh with invalid token."""
        # Setup mock to raise exception
        override_auth_dependency.refresh_access_token.side_effect = InvalidTokenException()
        
        # Make request
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid_token",
            }
        )
        
        # Verify response
        assert response.status_code == 401
        data = response.json()
        assert "Invalid or expired refresh token" in data["detail"]
    
    def test_get_current_user(self, client, override_current_user, auth_headers):
        """Test getting current user info."""
        # Make request with auth headers
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == override_current_user.username
        assert data["email"] == override_current_user.email
        assert data["is_active"] is True
    
    def test_get_current_user_no_auth(self, client):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # FastAPI returns 403 when no credentials provided
    
    def test_revoke_tokens(self, client, override_auth_dependency, override_current_user, auth_headers):
        """Test revoking tokens."""
        # Setup mock
        override_auth_dependency.revoke_user_tokens.return_value = None
        
        # Make request
        response = client.post(
            "/api/v1/auth/revoke",
            json={"revoke_all": True},
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "Tokens revoked successfully" in data["message"]
        
        # Verify service was called
        override_auth_dependency.revoke_user_tokens.assert_called_once_with(
            override_current_user.id,
            revoke_all=True
        )