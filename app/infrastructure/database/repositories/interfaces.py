"""Repository interface definitions following SOLID principles."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.core.domain.entities import Build, SortedTaskList, Task


class TaskRepositoryInterface(ABC):
    """
    Abstract interface for task data access operations.
    
    Defines the contract for task persistence operations, allowing for
    different implementations (database, file, memory) while maintaining
    consistent business logic.
    """

    @abstractmethod
    async def get_task(self, name: str) -> Optional[Task]:
        """
        Retrieve a single task by name.
        
        Args:
            name: Unique task identifier
            
        Returns:
            Task entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_tasks(self, names: List[str]) -> Dict[str, Task]:
        """
        Retrieve multiple tasks by names.
        
        Args:
            names: List of task names to retrieve
            
        Returns:
            Dictionary mapping task names to Task entities
        """
        pass

    @abstractmethod
    async def get_all_tasks(self) -> Dict[str, Task]:
        """
        Retrieve all available tasks.
        
        Returns:
            Dictionary mapping task names to Task entities
        """
        pass

    @abstractmethod
    async def save_task(self, task: Task) -> None:
        """
        Save or update a task.
        
        Args:
            task: Task entity to save
        """
        pass

    @abstractmethod
    async def save_tasks(self, tasks: List[Task]) -> None:
        """
        Save or update multiple tasks.
        
        Args:
            tasks: List of Task entities to save
        """
        pass

    @abstractmethod
    async def delete_task(self, name: str) -> bool:
        """
        Delete a task by name.
        
        Args:
            name: Task name to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        pass

    @abstractmethod
    async def task_exists(self, name: str) -> bool:
        """
        Check if a task exists.
        
        Args:
            name: Task name to check
            
        Returns:
            True if task exists, False otherwise
        """
        pass


class BuildRepositoryInterface(ABC):
    """
    Abstract interface for build data access operations.
    
    Defines the contract for build persistence operations, supporting
    different storage backends while maintaining business logic consistency.
    """

    @abstractmethod
    async def get_build(self, name: str) -> Optional[Build]:
        """
        Retrieve a single build by name.
        
        Args:
            name: Unique build identifier
            
        Returns:
            Build entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_builds(self, names: List[str]) -> Dict[str, Build]:
        """
        Retrieve multiple builds by names.
        
        Args:
            names: List of build names to retrieve
            
        Returns:
            Dictionary mapping build names to Build entities
        """
        pass

    @abstractmethod
    async def get_all_builds(self) -> Dict[str, Build]:
        """
        Retrieve all available builds.
        
        Returns:
            Dictionary mapping build names to Build entities
        """
        pass

    @abstractmethod
    async def save_build(self, build: Build) -> None:
        """
        Save or update a build.
        
        Args:
            build: Build entity to save
        """
        pass

    @abstractmethod
    async def save_builds(self, builds: List[Build]) -> None:
        """
        Save or update multiple builds.
        
        Args:
            builds: List of Build entities to save
        """
        pass

    @abstractmethod
    async def delete_build(self, name: str) -> bool:
        """
        Delete a build by name.
        
        Args:
            name: Build name to delete
            
        Returns:
            True if build was deleted, False if not found
        """
        pass

    @abstractmethod
    async def build_exists(self, name: str) -> bool:
        """
        Check if a build exists.
        
        Args:
            name: Build name to check
            
        Returns:
            True if build exists, False otherwise
        """
        pass


class SortResultRepositoryInterface(ABC):
    """
    Abstract interface for sort result caching operations.
    
    Provides contract for caching topological sort results to improve
    performance by avoiding repeated calculations for unchanged builds.
    """

    @abstractmethod
    async def get_sort_result(self, build_name: str, config_hash: str) -> Optional[SortedTaskList]:
        """
        Retrieve cached sort result for a build.
        
        Args:
            build_name: Name of the build
            config_hash: Configuration hash for cache validation
            
        Returns:
            Cached sort result if valid, None otherwise
        """
        pass

    @abstractmethod
    async def save_sort_result(
        self, 
        result: SortedTaskList, 
        config_hash: str
    ) -> None:
        """
        Save sort result to cache.
        
        Args:
            result: Sort result to cache
            config_hash: Configuration hash for cache validation
        """
        pass

    @abstractmethod
    async def invalidate_sort_result(self, build_name: str) -> None:
        """
        Invalidate cached sort result for a build.
        
        Args:
            build_name: Name of the build to invalidate
        """
        pass

    @abstractmethod
    async def clear_all_cache(self) -> None:
        """Clear all cached sort results."""
        pass