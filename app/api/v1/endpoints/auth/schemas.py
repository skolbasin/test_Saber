"""Authentication API schemas."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class UserRegistrationRequest(BaseModel):
    """User registration request schema."""
    
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (3-50 characters)",
        example="john_doe"
    )
    email: EmailStr = Field(
        ...,
        description="User email address",
        example="john.doe@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 characters)",
        example="secure_password_123"
    )


class UserLoginRequest(BaseModel):
    """User login request schema."""
    
    username: str = Field(
        ...,
        description="Username",
        example="john_doe"
    )
    password: str = Field(
        ...,
        description="Password",
        example="secure_password_123"
    )


class TokenResponse(BaseModel):
    """Token response schema."""
    
    access_token: str = Field(
        ...,
        description="JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="Refresh token for obtaining new access tokens",
        example="abc123def456ghi789..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=1800
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str = Field(
        ...,
        description="Refresh token",
        example="abc123def456ghi789..."
    )


class UserResponse(BaseModel):
    """User response schema."""
    
    id: int = Field(
        ...,
        description="User unique identifier",
        example=1
    )
    username: str = Field(
        ...,
        description="Username",
        example="john_doe"
    )
    email: str = Field(
        ...,
        description="User email address",
        example="john.doe@example.com"
    )
    is_active: bool = Field(
        ...,
        description="Whether user account is active",
        example=True
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Account creation timestamp",
        example="2023-01-01T12:00:00Z"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Last account update timestamp",
        example="2023-01-01T12:00:00Z"
    )

    class Config:
        from_attributes = True


class RevokeTokensRequest(BaseModel):
    """Revoke tokens request schema."""
    
    revoke_all: bool = Field(
        default=False,
        description="Whether to revoke all user tokens",
        example=False
    )


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    error: str = Field(
        ...,
        description="Error message",
        example="Invalid credentials"
    )
    type: str = Field(
        ...,
        description="Error type",
        example="AuthenticationError"
    )