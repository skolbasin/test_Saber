"""Authentication service database models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class UserModel(Base):
    """
    Database model for user accounts.
    
    Represents user authentication and profile information.
    """
    
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique user identifier"
    )
    
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username"
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User email address"
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether user account is active"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Account creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last account update timestamp"
    )

    def __repr__(self) -> str:
        """String representation of user model."""
        return f"<UserModel(id={self.id}, username='{self.username}', email='{self.email}')>"


class RefreshTokenModel(Base):
    """
    Database model for refresh tokens.
    
    Stores refresh tokens for JWT authentication with expiry and revocation support.
    """
    
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique token identifier"
    )
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        doc="ID of user this token belongs to"
    )
    
    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="The refresh token string"
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Token expiration timestamp"
    )
    
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether token has been revoked"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Token creation timestamp"
    )

    def __repr__(self) -> str:
        """String representation of refresh token model."""
        return f"<RefreshTokenModel(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"