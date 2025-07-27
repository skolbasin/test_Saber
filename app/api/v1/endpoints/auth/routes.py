"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.api.dependencies import get_auth_service, get_current_active_user
from .schemas import (
    UserRegistrationRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    RevokeTokensRequest,
    ErrorResponse,
)
from app.core.auth.entities import User
from app.core.auth.exceptions import (
    InvalidCredentialsException,
    UserAlreadyExistsException,
    InvalidTokenException,
    ExpiredTokenException,
    RevokedTokenException,
    UserNotFoundException,
    InactiveUserException,
)
from app.core.auth.services import AuthenticationService

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with username, email, and password.",
    responses={
        201: {"description": "User successfully created"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        409: {"model": ErrorResponse, "description": "User already exists"},
    },
)
async def register_user(
    user_data: UserRegistrationRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> UserResponse:
    """
    Register a new user account.
    
    Creates a new user with the provided credentials. Username and email
    must be unique across the system.
    """
    try:
        user = await auth_service.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
        )
        return UserResponse.model_validate(user)
    except UserAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already exists: {e.message}",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user and return access and refresh tokens.",
    responses={
        200: {"description": "Login successful"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        400: {"model": ErrorResponse, "description": "Inactive user account"},
    },
)
async def login(
    credentials: UserLoginRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.
    
    Returns both access token (for API requests) and refresh token
    (for obtaining new access tokens when they expire).
    """
    try:
        token_pair = await auth_service.authenticate_user(
            username=credentials.username,
            password=credentials.password,
        )
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )
    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    except InactiveUserException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive",
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Use refresh token to obtain a new access token.",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    When access token expires, use this endpoint with refresh token
    to obtain a new access token without re-authentication.
    """
    try:
        token_pair = await auth_service.refresh_access_token(request.refresh_token)
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )
    except (InvalidTokenException, ExpiredTokenException, RevokedTokenException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.post(
    "/revoke",
    summary="Revoke tokens",
    description="Revoke current user's refresh tokens.",
    responses={
        200: {"description": "Tokens revoked successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def revoke_tokens(
    request: RevokeTokensRequest,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> dict:
    """
    Revoke user's refresh tokens.
    
    Optionally revoke all tokens for the user or just the current session.
    This is useful for logout functionality and security purposes.
    """
    try:
        await auth_service.revoke_user_tokens(current_user.id, revoke_all=request.revoke_all)
        return {"message": "Tokens revoked successfully"}
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about currently authenticated user.",
    responses={
        200: {"description": "User information retrieved"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Get current authenticated user information.
    
    Returns details about the currently authenticated user based on
    the provided access token.
    """
    return UserResponse.model_validate(current_user)