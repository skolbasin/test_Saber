"""Tests for authentication entities."""

import pytest
from datetime import datetime, timedelta

from app.core.auth.entities import User, RefreshToken, TokenPair, TokenPayload


class TestUser:
    """Test cases for User entity."""

    def test_valid_user_creation(self):
        """Test creating valid user."""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
            is_active=True,
        )
        
        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_123"
        assert user.is_active is True

    def test_user_empty_username_raises_error(self):
        """Test that empty username raises ValueError."""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            User(
                id=1,
                username="",
                email="test@example.com",
                hashed_password="hashed_password_123",
            )

    def test_user_empty_email_raises_error(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Email cannot be empty"):
            User(
                id=1,
                username="testuser",
                email="",
                hashed_password="hashed_password_123",
            )

    def test_user_empty_password_raises_error(self):
        """Test that empty password raises ValueError."""
        with pytest.raises(ValueError, match="Hashed password cannot be empty"):
            User(
                id=1,
                username="testuser",
                email="test@example.com",
                hashed_password="",
            )

    def test_user_invalid_email_raises_error(self):
        """Test that invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            User(
                id=1,
                username="testuser",
                email="invalid_email",
                hashed_password="hashed_password_123",
            )

    def test_user_defaults(self):
        """Test user default values."""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
        )
        
        assert user.is_active is True
        assert user.created_at is None
        assert user.updated_at is None


class TestRefreshToken:
    """Test cases for RefreshToken entity."""

    def test_valid_refresh_token_creation(self):
        """Test creating valid refresh token."""
        expires_at = datetime.utcnow() + timedelta(days=7)
        token = RefreshToken(
            id=1,
            user_id=123,
            token="refresh_token_string",
            expires_at=expires_at,
        )
        
        assert token.id == 1
        assert token.user_id == 123
        assert token.token == "refresh_token_string"
        assert token.expires_at == expires_at
        assert token.is_revoked is False

    def test_refresh_token_empty_token_raises_error(self):
        """Test that empty token raises ValueError."""
        with pytest.raises(ValueError, match="Token cannot be empty"):
            RefreshToken(
                id=1,
                user_id=123,
                token="",
                expires_at=datetime.utcnow() + timedelta(days=7),
            )

    def test_refresh_token_invalid_user_id_raises_error(self):
        """Test that invalid user ID raises ValueError."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            RefreshToken(
                id=1,
                user_id=0,
                token="refresh_token_string",
                expires_at=datetime.utcnow() + timedelta(days=7),
            )

    def test_refresh_token_is_expired(self):
        """Test refresh token expiration check."""
        expired_token = RefreshToken(
            id=1,
            user_id=123,
            token="expired_token",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        )
        
        valid_token = RefreshToken(
            id=2,
            user_id=123,
            token="valid_token",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        
        assert expired_token.is_expired() is True
        assert valid_token.is_expired() is False

    def test_refresh_token_is_valid(self):
        """Test refresh token validity check."""
        valid_token = RefreshToken(
            id=1,
            user_id=123,
            token="valid_token",
            expires_at=datetime.utcnow() + timedelta(days=7),
            is_revoked=False,
        )
        
        expired_token = RefreshToken(
            id=2,
            user_id=123,
            token="expired_token",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
            is_revoked=False,
        )
        
        revoked_token = RefreshToken(
            id=3,
            user_id=123,
            token="revoked_token",
            expires_at=datetime.utcnow() + timedelta(days=7),
            is_revoked=True,
        )
        
        assert valid_token.is_valid() is True
        assert expired_token.is_valid() is False
        assert revoked_token.is_valid() is False


class TestTokenPair:
    """Test cases for TokenPair entity."""

    def test_valid_token_pair_creation(self):
        """Test creating valid token pair."""
        token_pair = TokenPair(
            access_token="access_token_string",
            refresh_token="refresh_token_string",
            token_type="bearer",
            expires_in=3600,
        )
        
        assert token_pair.access_token == "access_token_string"
        assert token_pair.refresh_token == "refresh_token_string"
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in == 3600

    def test_token_pair_empty_access_token_raises_error(self):
        """Test that empty access token raises ValueError."""
        with pytest.raises(ValueError, match="Access token cannot be empty"):
            TokenPair(
                access_token="",
                refresh_token="refresh_token_string",
            )

    def test_token_pair_empty_refresh_token_raises_error(self):
        """Test that empty refresh token raises ValueError."""
        with pytest.raises(ValueError, match="Refresh token cannot be empty"):
            TokenPair(
                access_token="access_token_string",
                refresh_token="",
            )

    def test_token_pair_defaults(self):
        """Test token pair default values."""
        token_pair = TokenPair(
            access_token="access_token_string",
            refresh_token="refresh_token_string",
        )
        
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in == 3600


class TestTokenPayload:
    """Test cases for TokenPayload entity."""

    def test_valid_token_payload_creation(self):
        """Test creating valid token payload."""
        now = int(datetime.utcnow().timestamp())
        exp = now + 3600
        
        payload = TokenPayload(
            sub="123",
            username="testuser",
            exp=exp,
            iat=now,
            token_type="access",
        )
        
        assert payload.sub == "123"
        assert payload.username == "testuser"
        assert payload.exp == exp
        assert payload.iat == now
        assert payload.token_type == "access"

    def test_token_payload_empty_sub_raises_error(self):
        """Test that empty subject raises ValueError."""
        now = int(datetime.utcnow().timestamp())
        
        with pytest.raises(ValueError, match="Subject cannot be empty"):
            TokenPayload(
                sub="",
                username="testuser",
                exp=now + 3600,
                iat=now,
            )

    def test_token_payload_empty_username_raises_error(self):
        """Test that empty username raises ValueError."""
        now = int(datetime.utcnow().timestamp())
        
        with pytest.raises(ValueError, match="Username cannot be empty"):
            TokenPayload(
                sub="123",
                username="",
                exp=now + 3600,
                iat=now,
            )

    def test_token_payload_invalid_expiration_raises_error(self):
        """Test that invalid expiration raises ValueError."""
        now = int(datetime.utcnow().timestamp())
        
        with pytest.raises(ValueError, match="Expiration must be after issued time"):
            TokenPayload(
                sub="123",
                username="testuser",
                exp=now - 3600,
                iat=now,
            )

    def test_token_payload_defaults(self):
        """Test token payload default values."""
        now = int(datetime.utcnow().timestamp())
        
        payload = TokenPayload(
            sub="123",
            username="testuser",
            exp=now + 3600,
            iat=now,
        )
        
        assert payload.token_type == "access"