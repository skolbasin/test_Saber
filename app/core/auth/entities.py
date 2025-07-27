"""Authentication domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class User:
    """
    User entity for authentication.
    
    Attributes:
        id: Unique user identifier
        username: Unique username
        email: User email address
        hashed_password: Securely hashed password
        is_active: Whether user account is active
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    
    id: int
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate user data after initialization."""
        if not self.username:
            raise ValueError("Username cannot be empty")
        if not self.email:
            raise ValueError("Email cannot be empty")
        if not self.hashed_password:
            raise ValueError("Hashed password cannot be empty")
        if "@" not in self.email:
            raise ValueError("Invalid email format")


@dataclass(frozen=True)
class RefreshToken:
    """
    Refresh token entity for token management.
    
    Attributes:
        id: Unique token identifier
        user_id: User ID this token belongs to
        token: The actual refresh token string
        expires_at: Token expiration timestamp
        is_revoked: Whether token has been revoked
        created_at: Token creation timestamp
    """
    
    id: Optional[int]
    user_id: int
    token: str
    expires_at: datetime
    is_revoked: bool = False
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate refresh token data."""
        if not self.token:
            raise ValueError("Token cannot be empty")
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")

    def is_expired(self) -> bool:
        """Check if refresh token is expired."""
        return datetime.utcnow() >= self.expires_at

    def is_valid(self) -> bool:
        """Check if refresh token is valid (not expired and not revoked)."""
        return not self.is_expired() and not self.is_revoked


@dataclass(frozen=True)
class TokenPair:
    """
    Access and refresh token pair.
    
    Attributes:
        access_token: JWT access token
        refresh_token: Refresh token string
        token_type: Token type (typically "bearer")
        expires_in: Access token expiration time in seconds
    """
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

    def __post_init__(self) -> None:
        """Validate token pair data."""
        if not self.access_token:
            raise ValueError("Access token cannot be empty")
        if not self.refresh_token:
            raise ValueError("Refresh token cannot be empty")


@dataclass(frozen=True)
class TokenPayload:
    """
    JWT token payload data.
    
    Attributes:
        sub: Subject (user ID)
        username: Username
        exp: Expiration timestamp
        iat: Issued at timestamp
        token_type: Type of token (access/refresh)
    """
    
    sub: str
    username: str
    exp: int
    iat: int
    token_type: str = "access"

    def __post_init__(self) -> None:
        """Validate token payload data."""
        if not self.sub:
            raise ValueError("Subject cannot be empty")
        if not self.username:
            raise ValueError("Username cannot be empty")
        if self.exp <= self.iat:
            raise ValueError("Expiration must be after issued time")