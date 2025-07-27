"""Task management service implementation."""

from typing import Dict, List, Optional

from app.core.domain.entities import Task
from app.core.exceptions import TaskNotFoundException, InvalidTaskDependencyException
from app.infrastructure.database.repositories.interfaces import TaskRepositoryInterface
from .interfaces import TaskServiceInterface, ConfigurationServiceInterface


class TaskService(TaskServiceInterface):
    """
    Task management service with validation and configuration support.
    
    Provides high-level task operations with business logic validation,
    dependency checking, and integration with configuration management.
    """

    def __init__(
        self,
        task_repository: TaskRepositoryInterface,
        config_service: ConfigurationServiceInterface,
    ) -> None:
        """
        Initialize task service with dependencies.
        
        Args:
            task_repository: Task data access interface
            config_service: Configuration management service
        """
        self._task_repository = task_repository
        self._config_service = config_service

    async def get_task(self, name: str) -> Optional[Task]:
        """
        Retrieve single task by name.
        
        Args:
            name: Task name to retrieve
            
        Returns:
            Task entity if found, None otherwise
        """
        return await self._task_repository.get_task(name)

    async def get_tasks(self, names: List[str]) -> Dict[str, Task]:
        """
        Retrieve multiple tasks by names efficiently.
        
        Args:
            names: List of task names to retrieve
            
        Returns:
            Dictionary mapping task names to Task entities
        """
        if not names:
            return {}
        return await self._task_repository.get_tasks(names)

    async def get_all_tasks(self) -> Dict[str, Task]:
        """
        Retrieve all available tasks from repository.
        
        Returns:
            Dictionary mapping task names to Task entities
        """
        return await self._task_repository.get_all_tasks()

    async def create_task(self, task: Task) -> Task:
        """
        Create new task with comprehensive validation.
        
        Args:
            task: Task entity to create
            
        Returns:
            Created task entity
            
        Raises:
            InvalidTaskDependencyException: If task has invalid dependencies
        """
        await self._validate_task_dependencies(task)
        
        await self._task_repository.save_task(task)
        
        created_task = await self._task_repository.get_task(task.name)
        if not created_task:
            raise TaskNotFoundException(task.name)
            
        return created_task

    async def update_task(self, task: Task) -> Task:
        """
        Update existing task with validation.
        
        Args:
            task: Task entity to update
            
        Returns:
            Updated task entity
            
        Raises:
            TaskNotFoundException: If task does not exist
            InvalidTaskDependencyException: If task has invalid dependencies
        """
        existing_task = await self._task_repository.get_task(task.name)
        if not existing_task:
            raise TaskNotFoundException(task.name)
            
        await self._validate_task_dependencies(task)
        
        await self._task_repository.save_task(task)
        
        updated_task = await self._task_repository.get_task(task.name)
        if not updated_task:
            raise TaskNotFoundException(task.name)
            
        return updated_task

    async def delete_task(self, name: str) -> bool:
        """
        Delete task by name with dependency validation.
        
        Args:
            name: Task name to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        if not await self._task_repository.task_exists(name):
            return False
            
        await self._validate_task_deletion(name)
        
        return await self._task_repository.delete_task(name)

    async def reload_tasks_from_config(self) -> int:
        """
        Reload all tasks from configuration files.
        
        Returns:
            Number of tasks loaded
            
        Raises:
            ConfigurationException: If configuration is invalid
        """
        from app.config import get_settings
        settings = get_settings()
        
        tasks = await self._config_service.load_tasks_config(settings.tasks_config_path)
        
        if tasks:
            task_list = list(tasks.values())
            await self._task_repository.save_tasks(task_list)
            
        return len(tasks)

    async def _validate_task_dependencies(self, task: Task) -> None:
        """
        Validate that all task dependencies exist.
        
        Args:
            task: Task to validate
            
        Raises:
            InvalidTaskDependencyException: If dependencies are invalid
        """
        if not task.dependencies:
            return
            
        all_tasks = await self._task_repository.get_all_tasks()
        existing_deps = set(all_tasks.keys())
        
        missing_deps = task.dependencies - existing_deps - {task.name}
        
        if missing_deps:
            raise InvalidTaskDependencyException(task.name, list(missing_deps))

    async def _validate_task_deletion(self, task_name: str) -> None:
        """
        Validate that task can be safely deleted.
        
        Args:
            task_name: Name of task to delete
            
        Raises:
            InvalidTaskDependencyException: If other tasks depend on this task
        """
        all_tasks = await self._task_repository.get_all_tasks()
        
        dependent_tasks = []
        for name, task in all_tasks.items():
            if task_name in task.dependencies:
                dependent_tasks.append(name)
        
        if dependent_tasks:
            raise InvalidTaskDependencyException(
                task_name,
                [f"Task is required by: {', '.join(dependent_tasks)}"]
            )