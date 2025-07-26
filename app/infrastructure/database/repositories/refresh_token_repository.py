"""Refresh token repository implementation."""

from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from app.core.auth.entities import RefreshToken
from app.core.services.auth.models import RefreshTokenModel


class SqlRefreshTokenRepository:
    """SQLAlchemy implementation of refresh token repository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize refresh token repository.
        
        Args:
            session: Database session
        """
        self._session = session

    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """
        Get refresh token by token string.
        
        Args:
            token: Refresh token string
            
        Returns:
            RefreshToken entity if found, None otherwise
        """
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token == token)
        )
        token_model = result.scalar_one_or_none()
        
        if token_model:
            return self._model_to_entity(token_model)
        return None

    async def save_refresh_token(
        self,
        refresh_token: RefreshToken,
    ) -> RefreshToken:
        """
        Save new refresh token.
        
        Args:
            refresh_token: RefreshToken entity to save
            
        Returns:
            Created RefreshToken entity
        """
        token_model = RefreshTokenModel(
            user_id=refresh_token.user_id,
            token=refresh_token.token,
            expires_at=refresh_token.expires_at,
            is_revoked=refresh_token.is_revoked,
        )
        
        self._session.add(token_model)
        await self._session.flush()
        return self._model_to_entity(token_model)

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke refresh token.
        
        Args:
            token: Refresh token string
            
        Returns:
            True if token was revoked, False if not found
        """
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token == token)
            .values(is_revoked=True)
        )
        
        return result.rowcount > 0

    async def revoke_user_tokens(self, user_id: int) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens revoked
        """
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(
                and_(
                    RefreshTokenModel.user_id == user_id,
                    RefreshTokenModel.is_revoked == False
                )
            )
            .values(is_revoked=True)
        )
        
        return result.rowcount

    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired refresh tokens from database.
        
        Returns:
            Number of tokens removed
        """
        now = datetime.utcnow()
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.expires_at < now)
        )
        expired_tokens = result.scalars().all()
        
        for token_model in expired_tokens:
            await self._session.delete(token_model)
        
        await self._session.flush()
        return len(expired_tokens)

    def _model_to_entity(self, model: RefreshTokenModel) -> RefreshToken:
        """
        Convert database model to domain entity.
        
        Args:
            model: RefreshToken database model
            
        Returns:
            RefreshToken domain entity
        """
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token=model.token,
            expires_at=model.expires_at,
            is_revoked=model.is_revoked,
            created_at=model.created_at,
        )