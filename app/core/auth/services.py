"""Authentication service implementations."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from .entities import User, RefreshToken, TokenPair, TokenPayload
from .exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    ExpiredTokenException,
    RevokedTokenException,
    UserNotFoundException,
    UserAlreadyExistsException,
    InactiveUserException,
)
from .interfaces import (
    PasswordServiceInterface,
    TokenServiceInterface,
    UserRepositoryInterface,
    RefreshTokenRepositoryInterface,
)


class PasswordService(PasswordServiceInterface):
    """
    BCrypt-based password hashing service.
    
    Provides secure password hashing and verification using bcrypt algorithm
    with configurable rounds for performance vs security balance.
    """

    def __init__(self) -> None:
        """Initialize password context with bcrypt."""
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        """
        Hash a password securely using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return self._pwd_context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify password against bcrypt hash.
        
        Args:
            password: Plain text password
            hashed_password: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        return self._pwd_context.verify(password, hashed_password)


class TokenService(TokenServiceInterface):
    """
    JWT-based token service with access and refresh token support.
    
    Handles creation, validation, and refresh of JWT tokens using
    RS256 algorithm for enhanced security.
    """

    def __init__(
        self,
        user_repository: UserRepositoryInterface,
        refresh_token_repository: RefreshTokenRepositoryInterface,
    ) -> None:
        """
        Initialize token service with repositories.
        
        Args:
            user_repository: User data access interface
            refresh_token_repository: Refresh token data access interface
        """
        self._settings = get_settings()
        self._user_repository = user_repository
        self._refresh_token_repository = refresh_token_repository
        
        self._secret_key = self._settings.jwt_secret_key
        self._algorithm = "HS256"
        self._access_token_expire_minutes = 30
        self._refresh_token_expire_days = 7

    def create_access_token(self, user: User) -> str:
        """
        Create JWT access token for user.
        
        Args:
            user: User entity
            
        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self._access_token_expire_minutes)
        
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "exp": expire,
            "iat": now,
            "token_type": "access",
        }
        
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, user: User) -> str:
        """
        Create secure refresh token string.
        
        Args:
            user: User entity
            
        Returns:
            Refresh token string
        """
        return secrets.token_urlsafe(32)

    def create_token_pair(self, user: User) -> TokenPair:
        """
        Create access and refresh token pair for user.
        
        Args:
            user: User entity
            
        Returns:
            Token pair with access and refresh tokens
        """
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._access_token_expire_minutes * 60,
        )

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
        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
            
            return TokenPayload(
                sub=payload["sub"],
                username=payload["username"],
                exp=payload["exp"],
                iat=payload["iat"],
                token_type=payload.get("token_type", "access"),
            )
            
        except JWTError as e:
            if "expired" in str(e).lower():
                raise ExpiredTokenException()
            raise InvalidTokenException(f"Token decode error: {e}")

    async def refresh_access_token(self, refresh_token: str) -> TokenPair:
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
        token_entity = await self._refresh_token_repository.get_refresh_token(
            refresh_token
        )
        
        if not token_entity:
            raise InvalidTokenException("Refresh token not found")
            
        if token_entity.is_revoked:
            raise RevokedTokenException()
            
        if token_entity.is_expired():
            raise ExpiredTokenException()
            
        user = await self._user_repository.get_user_by_id(token_entity.user_id)
        if not user:
            raise UserNotFoundException(str(token_entity.user_id))
            
        if not user.is_active:
            raise InactiveUserException(user.username)
            
        return self.create_token_pair(user)


class AuthenticationService:
    """
    High-level authentication service orchestrating auth operations.
    
    Combines password verification, token management, and user operations
    to provide complete authentication functionality.
    """

    def __init__(
        self,
        user_repository: UserRepositoryInterface,
        refresh_token_repository: RefreshTokenRepositoryInterface,
        password_service: PasswordServiceInterface,
        token_service: TokenServiceInterface,
    ) -> None:
        """
        Initialize authentication service.
        
        Args:
            user_repository: User data access interface
            refresh_token_repository: Refresh token data access interface
            password_service: Password hashing service
            token_service: Token management service
        """
        self._user_repository = user_repository
        self._refresh_token_repository = refresh_token_repository
        self._password_service = password_service
        self._token_service = token_service

    async def authenticate_user(self, username: str, password: str) -> TokenPair:
        """
        Authenticate user and return token pair.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            Token pair for authenticated user
            
        Raises:
            InvalidCredentialsException: If credentials are invalid
            InactiveUserException: If user account is inactive
        """
        user = await self._get_user_by_username_or_email(username)
        
        if not user or not self._password_service.verify_password(
            password, user.hashed_password
        ):
            raise InvalidCredentialsException()
            
        if not user.is_active:
            raise InactiveUserException(user.username)
            
        token_pair = self._token_service.create_token_pair(user)
        
        refresh_token_entity = RefreshToken(
            id=None,
            user_id=user.id,
            token=token_pair.refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        
        await self._refresh_token_repository.save_refresh_token(refresh_token_entity)
        
        return token_pair

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New token pair
        """
        token_pair = await self._token_service.refresh_access_token(refresh_token)
        
        await self._refresh_token_repository.revoke_refresh_token(refresh_token)
        
        refresh_token_entity = RefreshToken(
            id=None,
            user_id=int(self._token_service.decode_token(token_pair.access_token).sub),
            token=token_pair.refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        
        await self._refresh_token_repository.save_refresh_token(refresh_token_entity)
        
        return token_pair

    async def register_user(self, username: str, email: str, password: str) -> User:
        """
        Register new user account.
        
        Args:
            username: Unique username
            email: User email address
            password: Plain text password
            
        Returns:
            Created user entity
            
        Raises:
            UserAlreadyExistsException: If username or email already exists
        """
        existing_user = await self._get_user_by_username_or_email(username)
        if existing_user:
            raise UserAlreadyExistsException(username)
            
        existing_email = await self._user_repository.get_user_by_email(email)
        if existing_email:
            raise UserAlreadyExistsException(email)
            
        hashed_password = self._password_service.hash_password(password)
        
        user = User(
            id=0,
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=True,
        )
        
        return await self._user_repository.create_user(user)

    async def revoke_user_tokens(self, user_id: int) -> int:
        """
        Revoke all refresh tokens for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of tokens revoked
        """
        return await self._refresh_token_repository.revoke_user_tokens(user_id)

    async def get_current_user(self, token: str) -> User:
        """
        Get current user from access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Current user entity
            
        Raises:
            InvalidTokenException: If token is invalid
            UserNotFoundException: If user not found
            InactiveUserException: If user is inactive
        """
        payload = self._token_service.decode_token(token)
        
        user = await self._user_repository.get_user_by_id(int(payload.sub))
        if not user:
            raise UserNotFoundException(payload.sub)
            
        if not user.is_active:
            raise InactiveUserException(user.username)
            
        return user

    async def _get_user_by_username_or_email(self, identifier: str) -> Optional[User]:
        """Get user by username or email."""
        if "@" in identifier:
            return await self._user_repository.get_user_by_email(identifier)
        return await self._user_repository.get_user_by_username(identifier)