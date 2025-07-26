"""Database connection management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class DatabaseManager:
    """
    Database connection and session management.

    Handles async database connections, session creation, and lifecycle management
    following the async context manager pattern for proper resource cleanup.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize database manager.

        Args:
            settings: Application settings containing database configuration
        """
        self.settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        self._engine = create_async_engine(
            self.settings.database_url,
            echo=self.settings.debug,
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic cleanup.

        Yields:
            Async database session

        Raises:
            RuntimeError: If database manager not initialized
        """
        if not self._session_factory:
            raise RuntimeError("Database manager not initialized")

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @property
    def engine(self) -> AsyncEngine:
        """
        Get database engine.

        Returns:
            Async database engine

        Raises:
            RuntimeError: If database manager not initialized
        """
        if not self._engine:
            raise RuntimeError("Database manager not initialized")
        return self._engine


db_manager = DatabaseManager(Settings())