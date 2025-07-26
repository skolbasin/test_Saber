"""SQLAlchemy implementation of build repository."""

from typing import Dict, List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.entities import Build
from app.core.domain.enums import BuildStatus
from app.core.services.builds.models import BuildModel
from .interfaces import BuildRepositoryInterface


class SqlBuildRepository(BuildRepositoryInterface):
    """
    SQLAlchemy-based implementation of build repository.
    
    Provides persistent storage for build entities using async SQLAlchemy
    with proper transaction management and error handling.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def get_build(self, name: str) -> Optional[Build]:
        """
        Retrieve a single build by name.
        
        Args:
            name: Unique build identifier
            
        Returns:
            Build entity if found, None otherwise
        """
        stmt = select(BuildModel).where(BuildModel.name == name)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
            
        return self._model_to_entity(model)

    async def get_builds(self, names: List[str]) -> Dict[str, Build]:
        """
        Retrieve multiple builds by names.
        
        Args:
            names: List of build names to retrieve
            
        Returns:
            Dictionary mapping build names to Build entities
        """
        if not names:
            return {}
            
        stmt = select(BuildModel).where(BuildModel.name.in_(names))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return {
            model.name: self._model_to_entity(model)
            for model in models
        }

    async def get_all_builds(self) -> Dict[str, Build]:
        """
        Retrieve all available builds.
        
        Returns:
            Dictionary mapping build names to Build entities
        """
        stmt = select(BuildModel)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return {
            model.name: self._model_to_entity(model)
            for model in models
        }

    async def save_build(self, build: Build) -> Build:
        """
        Save or update a build.
        
        Args:
            build: Build entity to save
            
        Returns:
            Saved build entity
        """
        model = await self._get_or_create_model(build.name)
        self._update_model_from_entity(model, build)
        
        self.session.add(model)
        await self.session.flush()
        return self._model_to_entity(model)

    async def save_builds(self, builds: List[Build]) -> None:
        """
        Save or update multiple builds efficiently.
        
        Args:
            builds: List of Build entities to save
        """
        if not builds:
            return
            
        build_names = [build.name for build in builds]
        existing_models = await self._get_existing_models(build_names)
        
        for build in builds:
            if build.name in existing_models:
                model = existing_models[build.name]
            else:
                model = BuildModel(name=build.name)
                
            self._update_model_from_entity(model, build)
            self.session.add(model)
        
        await self.session.flush()

    async def delete_build(self, name: str) -> bool:
        """
        Delete a build by name.
        
        Args:
            name: Build name to delete
            
        Returns:
            True if build was deleted, False if not found
        """
        stmt = delete(BuildModel).where(BuildModel.name == name)
        result = await self.session.execute(stmt)
        await self.session.flush()
        
        return result.rowcount > 0

    async def build_exists(self, name: str) -> bool:
        """
        Check if a build exists.
        
        Args:
            name: Build name to check
            
        Returns:
            True if build exists, False otherwise
        """
        stmt = select(BuildModel.name).where(BuildModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _get_or_create_model(self, name: str) -> BuildModel:
        """Get existing model or create new one."""
        stmt = select(BuildModel).where(BuildModel.name == name)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            model = BuildModel(name=name)
            
        return model

    async def _get_existing_models(self, names: List[str]) -> Dict[str, BuildModel]:
        """Get existing models for batch operations."""
        stmt = select(BuildModel).where(BuildModel.name.in_(names))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return {model.name: model for model in models}

    def _model_to_entity(self, model: BuildModel) -> Build:
        """Convert database model to domain entity."""
        tasks = []
        if model.tasks:
            if isinstance(model.tasks, list):
                tasks = model.tasks
            else:
                tasks = model.tasks.split(',') if model.tasks else []
        
        return Build(
            name=model.name,
            tasks=tasks,
            status=BuildStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            error_message=model.error_message,
        )

    def _update_model_from_entity(self, model: BuildModel, entity: Build) -> None:
        """Update database model from domain entity."""
        model.tasks = entity.tasks
        model.status = entity.status.value
        model.error_message = entity.error_message
        
        if entity.updated_at:
            model.updated_at = entity.updated_at