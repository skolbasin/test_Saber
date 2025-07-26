"""User repository implementation."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.auth.entities import User
from app.core.auth.exceptions import UserAlreadyExistsException
from app.core.services.auth.models import UserModel


class SqlUserRepository:
    """SQLAlchemy implementation of user repository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize user repository.
        
        Args:
            session: Database session
        """
        self._session = session

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User entity if found, None otherwise
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user_model = result.scalar_one_or_none()
        
        if user_model:
            return self._model_to_entity(user_model)
        return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User entity if found, None otherwise
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        user_model = result.scalar_one_or_none()
        
        if user_model:
            return self._model_to_entity(user_model)
        return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email address
            
        Returns:
            User entity if found, None otherwise
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        user_model = result.scalar_one_or_none()
        
        if user_model:
            return self._model_to_entity(user_model)
        return None

    async def create_user(self, user: User) -> User:
        """
        Create new user.
        
        Args:
            user: User entity to create
            
        Returns:
            Created user entity with ID
            
        Raises:
            UserAlreadyExistsException: If username or email already exists
        """
        user_model = UserModel(
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
        )
        
        try:
            self._session.add(user_model)
            await self._session.flush()
            await self._session.refresh(user_model)
            return self._model_to_entity(user_model)
        except IntegrityError:
            await self._session.rollback()
            raise UserAlreadyExistsException(f"User with username '{user.username}' or email '{user.email}' already exists")

    async def update_user(self, user: User) -> User:
        """
        Update existing user.
        
        Args:
            user: User entity to update
            
        Returns:
            Updated user entity
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        user_model = result.scalar_one_or_none()
        
        if user_model:
            self._update_model_from_entity(user_model, user)
            await self._session.flush()
            return self._model_to_entity(user_model)
        return user

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user was deleted, False if not found
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user_model = result.scalar_one_or_none()
        
        if user_model:
            await self._session.delete(user_model)
            await self._session.flush()
            return True
        return False

    def _model_to_entity(self, model: UserModel) -> User:
        """
        Convert database model to domain entity.
        
        Args:
            model: User database model
            
        Returns:
            User domain entity
        """
        return User(
            id=model.id,
            username=model.username,
            email=model.email,
            hashed_password=model.hashed_password,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _update_model_from_entity(self, model: UserModel, entity: User) -> None:
        """
        Update database model from domain entity.
        
        Args:
            model: User database model
            entity: User domain entity
        """
        model.username = entity.username
        model.email = entity.email
        model.hashed_password = entity.hashed_password
        model.is_active = entity.is_active