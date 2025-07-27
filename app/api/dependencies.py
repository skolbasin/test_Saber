"""FastAPI dependency injection setup."""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.entities import User
from app.core.auth.exceptions import (
    InvalidTokenException,
    ExpiredTokenException,
    UserNotFoundException,
)
from app.core.auth.services import AuthenticationService
from app.core.services.build_service import BuildService
from app.core.services.topology_service import TopologyService
from app.infrastructure.database.session import get_session
from app.infrastructure.database.repositories.build_repository import SqlBuildRepository
from app.infrastructure.database.repositories.task_repository import SqlTaskRepository
from app.infrastructure.database.repositories.user_repository import SqlUserRepository
from app.infrastructure.database.repositories.refresh_token_repository import SqlRefreshTokenRepository
from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.cache.redis_client import get_redis_client

security = HTTPBearer()

_auth_service: AuthenticationService = None
_build_service: BuildService = None


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide database session for dependency injection.

    Yields:
        AsyncSession: Database session
    """
    async for session in get_session():
        yield session


async def get_auth_service(
        session: AsyncSession = Depends(get_database_session)
) -> AuthenticationService:
    """
    Provide authentication service for dependency injection.

    Args:
        session: Database session

    Returns:
        AuthenticationService: Authentication service instance
    """
    global _auth_service
    if _auth_service is None:
        from app.core.auth.services import PasswordService, TokenService

        user_repo = SqlUserRepository(session)
        refresh_token_repo = SqlRefreshTokenRepository(session)
        password_service = PasswordService()
        token_service = TokenService(user_repo, refresh_token_repo)

        _auth_service = AuthenticationService(
            user_repo,
            refresh_token_repo,
            password_service,
            token_service,
        )

    return _auth_service


async def get_build_service(
        session: AsyncSession = Depends(get_database_session)
) -> BuildService:
    """
    Provide build service for dependency injection.

    Args:
        session: Database session

    Returns:
        BuildService: Build service instance
    """
    global _build_service
    if _build_service is None:
        build_repo = SqlBuildRepository(session)
        task_repo = SqlTaskRepository(session)
        topology_service = TopologyService()

        redis_client = get_redis_client()
        cache_service = CacheService(redis_client)

        _build_service = BuildService(build_repo, task_repo, topology_service, cache_service)

    return _build_service


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        auth_service: AuthenticationService = Depends(get_auth_service),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP bearer token credentials
        auth_service: Authentication service

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    try:
        user = await auth_service.get_current_user(token)
        return user
    except InvalidTokenException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ExpiredTokenException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
        current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (user must be active).

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_optional_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        auth_service: AuthenticationService = Depends(get_auth_service),
) -> User | None:
    """
    Get current user if token is provided and valid, None otherwise.

    Args:
        credentials: HTTP bearer token credentials (optional)
        auth_service: Authentication service

    Returns:
        User or None: Current user if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, auth_service)
    except HTTPException:
        return None