"""SQLAlchemy implementation of task repository."""

from typing import Dict, List, Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.entities import Task
from app.core.domain.enums import TaskStatus
from app.core.services.tasks.models import TaskModel
from .interfaces import TaskRepositoryInterface


class SqlTaskRepository(TaskRepositoryInterface):
    """
    SQLAlchemy-based implementation of task repository.
    
    Provides persistent storage for task entities using async SQLAlchemy
    with proper transaction management and error handling.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def get_task(self, name: str) -> Optional[Task]:
        """
        Retrieve a single task by name.
        
        Args:
            name: Unique task identifier
            
        Returns:
            Task entity if found, None otherwise
        """
        stmt = select(TaskModel).where(TaskModel.name == name)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
            
        return self._model_to_entity(model)

    async def get_tasks(self, names: List[str]) -> Dict[str, Task]:
        """
        Retrieve multiple tasks by names.
        
        Args:
            names: List of task names to retrieve
            
        Returns:
            Dictionary mapping task names to Task entities
        """
        if not names:
            return {}
            
        stmt = select(TaskModel).where(TaskModel.name.in_(names))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return {
            model.name: self._model_to_entity(model)
            for model in models
        }

    async def get_all_tasks(self) -> Dict[str, Task]:
        """
        Retrieve all available tasks.
        
        Returns:
            Dictionary mapping task names to Task entities
        """
        stmt = select(TaskModel)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return {
            model.name: self._model_to_entity(model)
            for model in models
        }

    async def save_task(self, task: Task) -> Task:
        """
        Save or update a task.
        
        Args:
            task: Task entity to save
            
        Returns:
            Saved task entity
        """
        model = await self._get_or_create_model(task.name)
        self._update_model_from_entity(model, task)
        
        self.session.add(model)
        await self.session.flush()
        return self._model_to_entity(model)

    async def save_tasks(self, tasks: List[Task]) -> None:
        """
        Save or update multiple tasks efficiently.
        
        Args:
            tasks: List of Task entities to save
        """
        if not tasks:
            return
            
        task_names = [task.name for task in tasks]
        existing_models = await self._get_existing_models(task_names)
        
        for task in tasks:
            if task.name in existing_models:
                model = existing_models[task.name]
            else:
                model = TaskModel(name=task.name)
                
            self._update_model_from_entity(model, task)
            self.session.add(model)
        
        await self.session.flush()

    async def delete_task(self, name: str) -> bool:
        """
        Delete a task by name.
        
        Args:
            name: Task name to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        stmt = delete(TaskModel).where(TaskModel.name == name)
        result = await self.session.execute(stmt)
        await self.session.flush()
        
        return result.rowcount > 0

    async def task_exists(self, name: str) -> bool:
        """
        Check if a task exists.
        
        Args:
            name: Task name to check
            
        Returns:
            True if task exists, False otherwise
        """
        stmt = select(TaskModel.name).where(TaskModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _get_or_create_model(self, name: str) -> TaskModel:
        """Get existing model or create new one."""
        stmt = select(TaskModel).where(TaskModel.name == name)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            model = TaskModel(name=name)
            
        return model

    async def _get_existing_models(self, names: List[str]) -> Dict[str, TaskModel]:
        """Get existing models for batch operations."""
        stmt = select(TaskModel).where(TaskModel.name.in_(names))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return {model.name: model for model in models}

    def _model_to_entity(self, model: TaskModel) -> Task:
        """Convert database model to domain entity."""
        dependencies = set()
        if model.dependencies:
            if isinstance(model.dependencies, list):
                dependencies = set(model.dependencies)
            else:
                dependencies = set(model.dependencies.split(',')) if model.dependencies else set()
        
        return Task(
            name=model.name,
            dependencies=dependencies,
            status=TaskStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            error_message=model.error_message,
        )

    def _update_model_from_entity(self, model: TaskModel, entity: Task) -> None:
        """Update database model from domain entity."""
        model.dependencies = list(entity.dependencies)
        model.status = entity.status.value
        model.error_message = entity.error_message
        
        if entity.updated_at:
            model.updated_at = entity.updated_at