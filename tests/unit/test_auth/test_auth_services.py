"""Tests for authentication services."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.core.auth.entities import User, RefreshToken, TokenPair
from app.core.auth.exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    ExpiredTokenException,
    RevokedTokenException,
    UserNotFoundException,
    UserAlreadyExistsException,
    InactiveUserException,
)
from app.core.auth.services import PasswordService, TokenService, AuthenticationService


@pytest.fixture
def mock_user():
    """Create mock user."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$hashed_password",
        is_active=True,
    )


@pytest.fixture
def mock_user_repository():
    """Create mock user repository."""
    return AsyncMock()


@pytest.fixture
def mock_refresh_token_repository():
    """Create mock refresh token repository."""
    return AsyncMock()


@pytest.fixture
def password_service():
    """Create password service."""
    return PasswordService()


@pytest.fixture
def token_service(mock_user_repository, mock_refresh_token_repository):
    """Create token service with mocked dependencies."""
    return TokenService(mock_user_repository, mock_refresh_token_repository)


@pytest.fixture
def auth_service(
    mock_user_repository,
    mock_refresh_token_repository,
    password_service,
    token_service,
):
    """Create authentication service with mocked dependencies."""
    return AuthenticationService(
        mock_user_repository,
        mock_refresh_token_repository,
        password_service,
        token_service,
    )


class TestPasswordService:
    """Test cases for PasswordService."""

    def test_hash_password(self, password_service):
        """Test password hashing."""
        password = "test_password_123"
        hashed = password_service.hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_verify_password_correct(self, password_service):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = password_service.hash_password(password)
        
        assert password_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, password_service):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = password_service.hash_password(password)
        
        assert password_service.verify_password(wrong_password, hashed) is False

    def test_hash_password_different_results(self, password_service):
        """Test that same password produces different hashes."""
        password = "test_password_123"
        hash1 = password_service.hash_password(password)
        hash2 = password_service.hash_password(password)
        
        assert hash1 != hash2
        assert password_service.verify_password(password, hash1) is True
        assert password_service.verify_password(password, hash2) is True


class TestTokenService:
    """Test cases for TokenService."""

    @patch('app.core.auth.services.get_settings')
    def test_create_access_token(self, mock_settings, token_service, mock_user):
        """Test access token creation."""
        mock_settings.return_value.jwt_secret_key = "test_secret"
        
        token = token_service.create_access_token(mock_user)
        
        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count('.') == 2

    @patch('app.core.auth.services.secrets')
    def test_create_refresh_token(self, mock_secrets, token_service, mock_user):
        """Test refresh token creation."""
        mock_secrets.token_urlsafe.return_value = "mock_refresh_token"
        
        token = token_service.create_refresh_token(mock_user)
        
        assert token == "mock_refresh_token"
        mock_secrets.token_urlsafe.assert_called_once_with(32)

    @patch('app.core.auth.services.get_settings')
    @patch('app.core.auth.services.secrets')
    def test_create_token_pair(self, mock_secrets, mock_settings, token_service, mock_user):
        """Test token pair creation."""
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_secrets.token_urlsafe.return_value = "mock_refresh_token"
        
        token_pair = token_service.create_token_pair(mock_user)
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token.count('.') == 2
        assert token_pair.refresh_token == "mock_refresh_token"
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in == 1800

    @patch('app.core.auth.services.get_settings')
    def test_decode_token_valid(self, mock_settings, token_service, mock_user):
        """Test valid token decoding."""
        mock_settings.return_value.jwt_secret_key = "test_secret"
        
        token = token_service.create_access_token(mock_user)
        payload = token_service.decode_token(token)
        
        assert payload.sub == str(mock_user.id)
        assert payload.username == mock_user.username
        assert payload.token_type == "access"

    @patch('app.core.auth.services.get_settings')
    def test_decode_token_invalid(self, mock_settings, token_service):
        """Test invalid token decoding."""
        mock_settings.return_value.jwt_secret_key = "test_secret"
        
        with pytest.raises(InvalidTokenException):
            token_service.decode_token("invalid.jwt.token")

    @patch('app.core.auth.services.get_settings')
    def test_decode_token_expired(self, mock_settings, token_service):
        """Test expired token decoding."""
        mock_settings.return_value.jwt_secret_key = "test_secret"
        
        from jose import JWTError
        with patch('app.core.auth.services.jwt.decode') as mock_decode:
            mock_decode.side_effect = JWTError("Token has expired")
            
            with pytest.raises(ExpiredTokenException):
                token_service.decode_token("expired.jwt.token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(
        self,
        token_service,
        mock_user,
        mock_user_repository,
        mock_refresh_token_repository,
    ):
        """Test successful access token refresh."""
        refresh_token = RefreshToken(
            id=1,
            user_id=mock_user.id,
            token="valid_refresh_token",
            expires_at=datetime.utcnow() + timedelta(days=7),
            is_revoked=False,
        )
        
        mock_refresh_token_repository.get_refresh_token.return_value = refresh_token
        mock_user_repository.get_user_by_id.return_value = mock_user
        
        with patch.object(token_service, 'create_token_pair') as mock_create:
            mock_token_pair = TokenPair("new_access", "new_refresh", "bearer", 1800)
            mock_create.return_value = mock_token_pair
            
            result = await token_service.refresh_access_token("valid_refresh_token")
            
            assert result == mock_token_pair
            mock_refresh_token_repository.get_refresh_token.assert_called_once_with(
                "valid_refresh_token"
            )
            mock_user_repository.get_user_by_id.assert_called_once_with(mock_user.id)

    @pytest.mark.asyncio
    async def test_refresh_access_token_not_found(
        self, token_service, mock_refresh_token_repository
    ):
        """Test refresh token not found."""
        mock_refresh_token_repository.get_refresh_token.return_value = None
        
        with pytest.raises(InvalidTokenException, match="Refresh token not found"):
            await token_service.refresh_access_token("nonexistent_token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_revoked(
        self, token_service, mock_refresh_token_repository
    ):
        """Test revoked refresh token."""
        refresh_token = RefreshToken(
            id=1,
            user_id=1,
            token="revoked_token",
            expires_at=datetime.utcnow() + timedelta(days=7),
            is_revoked=True,
        )
        
        mock_refresh_token_repository.get_refresh_token.return_value = refresh_token
        
        with pytest.raises(RevokedTokenException):
            await token_service.refresh_access_token("revoked_token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_expired(
        self, token_service, mock_refresh_token_repository
    ):
        """Test expired refresh token."""
        refresh_token = RefreshToken(
            id=1,
            user_id=1,
            token="expired_token",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
            is_revoked=False,
        )
        
        mock_refresh_token_repository.get_refresh_token.return_value = refresh_token
        
        with pytest.raises(ExpiredTokenException):
            await token_service.refresh_access_token("expired_token")


class TestAuthenticationService:
    """Test cases for AuthenticationService."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self,
        auth_service,
        mock_user,
        mock_user_repository,
        mock_refresh_token_repository,
    ):
        """Test successful user authentication."""
        mock_user_repository.get_user_by_username.return_value = mock_user
        mock_refresh_token_repository.save_refresh_token.return_value = AsyncMock()
        
        with patch.object(auth_service._password_service, 'verify_password') as mock_verify:
            mock_verify.return_value = True
            
            with patch.object(auth_service._token_service, 'create_token_pair') as mock_create:
                mock_token_pair = TokenPair("access", "refresh", "bearer", 1800)
                mock_create.return_value = mock_token_pair
                
                result = await auth_service.authenticate_user("testuser", "password")
                
                assert result == mock_token_pair
                mock_verify.assert_called_once_with("password", mock_user.hashed_password)

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(
        self, auth_service, mock_user_repository
    ):
        """Test authentication with invalid credentials."""
        mock_user_repository.get_user_by_username.return_value = None
        
        with pytest.raises(InvalidCredentialsException):
            await auth_service.authenticate_user("nonexistent", "password")

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(
        self, auth_service, mock_user_repository
    ):
        """Test authentication with inactive user."""
        inactive_user = User(
            id=1,
            username="inactive",
            email="test@example.com",
            hashed_password="$2b$12$hashed",
            is_active=False,
        )
        
        mock_user_repository.get_user_by_username.return_value = inactive_user
        
        with patch.object(auth_service._password_service, 'verify_password') as mock_verify:
            mock_verify.return_value = True
            
            with pytest.raises(InactiveUserException):
                await auth_service.authenticate_user("inactive", "password")

    @pytest.mark.asyncio
    async def test_register_user_success(
        self, auth_service, mock_user_repository
    ):
        """Test successful user registration."""
        mock_user_repository.get_user_by_username.return_value = None
        mock_user_repository.get_user_by_email.return_value = None
        
        new_user = User(
            id=1,
            username="newuser",
            email="new@example.com",
            hashed_password="$2b$12$hashed",
            is_active=True,
        )
        mock_user_repository.create_user.return_value = new_user
        
        result = await auth_service.register_user("newuser", "new@example.com", "password")
        
        assert result == new_user
        mock_user_repository.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_already_exists(
        self, auth_service, mock_user, mock_user_repository
    ):
        """Test registration with existing username."""
        mock_user_repository.get_user_by_username.return_value = mock_user
        
        with pytest.raises(UserAlreadyExistsException):
            await auth_service.register_user("testuser", "new@example.com", "password")

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self, auth_service, mock_user, mock_user_repository
    ):
        """Test getting current user from token."""
        mock_user_repository.get_user_by_id.return_value = mock_user
        
        with patch.object(auth_service._token_service, 'decode_token') as mock_decode:
            from app.core.auth.entities import TokenPayload
            
            mock_payload = TokenPayload(
                sub=str(mock_user.id),
                username=mock_user.username,
                exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
                iat=int(datetime.utcnow().timestamp()),
            )
            mock_decode.return_value = mock_payload
            
            result = await auth_service.get_current_user("valid_token")
            
            assert result == mock_user
            mock_user_repository.get_user_by_id.assert_called_once_with(mock_user.id)

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(
        self, auth_service, mock_user_repository
    ):
        """Test getting current user when user not found."""
        mock_user_repository.get_user_by_id.return_value = None
        
        with patch.object(auth_service._token_service, 'decode_token') as mock_decode:
            from app.core.auth.entities import TokenPayload
            
            mock_payload = TokenPayload(
                sub="999",
                username="nonexistent",
                exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
                iat=int(datetime.utcnow().timestamp()),
            )
            mock_decode.return_value = mock_payload
            
            with pytest.raises(UserNotFoundException):
                await auth_service.get_current_user("valid_token")

    @pytest.mark.asyncio
    async def test_revoke_user_tokens(
        self, auth_service, mock_refresh_token_repository
    ):
        """Test revoking user tokens."""
        mock_refresh_token_repository.revoke_user_tokens.return_value = 3
        
        result = await auth_service.revoke_user_tokens(1)
        
        assert result == 3
        mock_refresh_token_repository.revoke_user_tokens.assert_called_once_with(1)