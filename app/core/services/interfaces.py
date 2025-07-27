"""Service interfaces following SOLID principles."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.core.domain.entities import Build, SortedTaskList, Task
from app.core.domain.enums import SortAlgorithm


class TopologyServiceInterface(ABC):
    """
    Interface for topological sorting operations.
    
    Provides contract for different topological sorting algorithms
    while maintaining consistent business logic across implementations.
    """

    @abstractmethod
    async def sort_tasks(
        self,
        build: Build,
        tasks: Dict[str, Task],
        algorithm: Optional[SortAlgorithm] = None,
    ) -> SortedTaskList:
        """
        Sort tasks in topological order based on dependencies.
        
        Args:
            build: Build entity containing task names
            tasks: Dictionary mapping task names to Task entities
            algorithm: Sorting algorithm to use (defaults to configured algorithm)
            
        Returns:
            Sorted task list with execution metadata
            
        Raises:
            CircularDependencyException: If circular dependencies detected
            TaskNotFoundException: If build references non-existent tasks
            TopologicalSortException: If sorting fails for other reasons
        """
        pass

    @abstractmethod
    def detect_cycles(self, tasks: Dict[str, Task]) -> List[List[str]]:
        """
        Detect circular dependencies in task graph.
        
        Args:
            tasks: Dictionary mapping task names to Task entities
            
        Returns:
            List of cycles, where each cycle is a list of task names
        """
        pass

    @abstractmethod
    def validate_dependencies(
        self, build: Build, tasks: Dict[str, Task]
    ) -> List[str]:
        """
        Validate that all task dependencies exist.
        
        Args:
            build: Build entity to validate
            tasks: Available tasks dictionary
            
        Returns:
            List of missing dependency names (empty if all valid)
        """
        pass


class TaskServiceInterface(ABC):
    """
    Interface for task management operations.
    
    Provides contract for task lifecycle management and validation
    operations across different storage implementations.
    """

    @abstractmethod
    async def get_task(self, name: str) -> Optional[Task]:
        """
        Retrieve single task by name.
        
        Args:
            name: Task name to retrieve
            
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
    async def create_task(self, task: Task) -> Task:
        """
        Create new task with validation.
        
        Args:
            task: Task entity to create
            
        Returns:
            Created task entity
            
        Raises:
            InvalidTaskDependencyException: If task has invalid dependencies
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def delete_task(self, name: str) -> bool:
        """
        Delete task by name.
        
        Args:
            name: Task name to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        pass

    @abstractmethod
    async def reload_tasks_from_config(self) -> int:
        """
        Reload tasks from configuration files.
        
        Returns:
            Number of tasks loaded
        """
        pass


class BuildServiceInterface(ABC):
    """
    Interface for build management operations.
    
    Provides contract for build lifecycle management and task orchestration
    operations across different storage implementations.
    """

    @abstractmethod
    async def get_build(self, name: str) -> Optional[Build]:
        """
        Retrieve single build by name.
        
        Args:
            name: Build name to retrieve
            
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
    async def create_build(self, build: Build) -> Build:
        """
        Create new build with validation.
        
        Args:
            build: Build entity to create
            
        Returns:
            Created build entity
            
        Raises:
            TaskNotFoundException: If build references non-existent tasks
        """
        pass

    @abstractmethod
    async def update_build(self, build: Build) -> Build:
        """
        Update existing build with validation.
        
        Args:
            build: Build entity to update
            
        Returns:
            Updated build entity
            
        Raises:
            BuildNotFoundException: If build does not exist
            TaskNotFoundException: If build references non-existent tasks
        """
        pass

    @abstractmethod
    async def delete_build(self, name: str) -> bool:
        """
        Delete build by name.
        
        Args:
            name: Build name to delete
            
        Returns:
            True if build was deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_sorted_tasks(
        self,
        build_name: str,
        algorithm: Optional[SortAlgorithm] = None,
        use_cache: bool = True,
    ) -> SortedTaskList:
        """
        Get topologically sorted tasks for a build.
        
        Args:
            build_name: Name of build to sort
            algorithm: Sorting algorithm to use
            use_cache: Whether to use cached results
            
        Returns:
            Sorted task list with execution metadata
            
        Raises:
            BuildNotFoundException: If build does not exist
            TaskNotFoundException: If build references non-existent tasks
            CircularDependencyException: If circular dependencies detected
        """
        pass

    @abstractmethod
    async def reload_builds_from_config(self) -> int:
        """
        Reload builds from configuration files.
        
        Returns:
            Number of builds loaded
        """
        pass


class ConfigurationServiceInterface(ABC):
    """
    Interface for configuration management operations.
    
    Provides contract for loading and validating YAML configuration
    files with proper error handling and caching.
    """

    @abstractmethod
    async def load_tasks_config(self, file_path: str) -> Dict[str, Task]:
        """
        Load tasks from YAML configuration file.
        
        Args:
            file_path: Path to tasks YAML file
            
        Returns:
            Dictionary mapping task names to Task entities
            
        Raises:
            ConfigurationException: If configuration is invalid
        """
        pass

    @abstractmethod
    async def load_builds_config(self, file_path: str) -> Dict[str, Build]:
        """
        Load builds from YAML configuration file.
        
        Args:
            file_path: Path to builds YAML file
            
        Returns:
            Dictionary mapping build names to Build entities
            
        Raises:
            ConfigurationException: If configuration is invalid
        """
        pass

    @abstractmethod
    async def validate_configuration(
        self, tasks: Dict[str, Task], builds: Dict[str, Build]
    ) -> List[str]:
        """
        Validate complete configuration for consistency.
        
        Args:
            tasks: Tasks dictionary to validate
            builds: Builds dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        pass

    @abstractmethod
    async def reload_all_configuration(self) -> tuple[int, int]:
        """
        Reload all configuration from files.
        
        Returns:
            Tuple of (tasks_loaded, builds_loaded)
        """
        pass