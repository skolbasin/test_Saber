"""Database session management."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.settings import get_settings

_async_session_maker: async_sessionmaker[AsyncSession] = None
_engine = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.

    Yields:
        AsyncSession: Database session
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_connections():
    """Close all database connections."""
    global _engine, _async_session_maker
    if _engine:
        await _engine.dispose()
        _engine = None
    _async_session_maker = None