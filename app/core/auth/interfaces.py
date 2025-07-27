"""Authentication service interfaces."""

from abc import ABC, abstractmethod
from typing import Optional

from .entities import User, RefreshToken, TokenPair, TokenPayload


class PasswordServiceInterface(ABC):
    """Interface for password hashing and verification."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """
        Hash a password securely.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        pass

    @abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hashed_password: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        pass


class TokenServiceInterface(ABC):
    """Interface for JWT token operations."""

    @abstractmethod
    def create_access_token(self, user: User) -> str:
        """
        Create JWT access token for user.
        
        Args:
            user: User entity
            
        Returns:
            JWT access token string
        """
        pass

    @abstractmethod
    def create_refresh_token(self, user: User) -> str:
        """
        Create refresh token for user.
        
        Args:
            user: User entity
            
        Returns:
            Refresh token string
        """
        pass

    @abstractmethod
    def create_token_pair(self, user: User) -> TokenPair:
        """
        Create access and refresh token pair.
        
        Args:
            user: User entity
            
        Returns:
            Token pair with access and refresh tokens
        """
        pass

    @abstractmethod
    def decode_token(self, token: str) -> TokenPayload:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload data
            
        Raises:
            InvalidTokenException: If token is invalid or malformed
            ExpiredTokenException: If token has expired
        """
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """
        Create new access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New token pair
            
        Raises:
            InvalidTokenException: If refresh token is invalid
            ExpiredTokenException: If refresh token has expired
            RevokedTokenException: If refresh token has been revoked
        """
        pass


class UserRepositoryInterface(ABC):
    """Interface for user data access operations."""

    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email address
            
        Returns:
            User entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """
        Create new user.
        
        Args:
            user: User entity to create
            
        Returns:
            Created user entity with ID
        """
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """
        Update existing user.
        
        Args:
            user: User entity to update
            
        Returns:
            Updated user entity
        """
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if user was deleted, False if not found
        """
        pass


class RefreshTokenRepositoryInterface(ABC):
    """Interface for refresh token data access operations."""

    @abstractmethod
    async def save_refresh_token(self, token: RefreshToken) -> RefreshToken:
        """
        Save refresh token.
        
        Args:
            token: Refresh token entity
            
        Returns:
            Saved refresh token with ID
        """
        pass

    @abstractmethod
    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """
        Get refresh token by token string.
        
        Args:
            token: Refresh token string
            
        Returns:
            Refresh token entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def revoke_refresh_token(self, token: str) -> bool:
        """
        Revoke refresh token.
        
        Args:
            token: Refresh token string
            
        Returns:
            True if token was revoked, False if not found
        """
        pass

    @abstractmethod
    async def revoke_user_tokens(self, user_id: int) -> int:
        """
        Revoke all refresh tokens for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of tokens revoked
        """
        pass

    @abstractmethod
    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired refresh tokens.
        
        Returns:
            Number of tokens removed
        """
        pass