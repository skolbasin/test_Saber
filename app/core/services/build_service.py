"""Build orchestration service implementation."""

import yaml
import os
from datetime import datetime
from typing import Dict, List, Optional

from app.core.domain.entities import Build, SortedTaskList, Task
from app.core.domain.enums import BuildStatus, SortAlgorithm, TaskStatus
from app.core.exceptions import (
    BuildNotFoundException,
    TaskNotFoundException,
    CircularDependencyException,
)
from app.infrastructure.database.repositories.interfaces import (
    BuildRepositoryInterface,
    TaskRepositoryInterface,
)
from app.infrastructure.cache.cache_service import CacheService
from .interfaces import BuildServiceInterface, TopologyServiceInterface


class BuildService(BuildServiceInterface):
    """
    High-performance build orchestration service.
    
    Manages build lifecycle, task orchestration, and dependency resolution
    with comprehensive error handling and optimized performance for CI/CD systems.
    """

    def __init__(
        self,
        build_repository: BuildRepositoryInterface,
        task_repository: TaskRepositoryInterface,
        topology_service: TopologyServiceInterface,
        cache_service: Optional[CacheService] = None,
    ):
        """
        Initialize build service with dependencies.
        
        Args:
            build_repository: Repository for build persistence
            task_repository: Repository for task persistence
            topology_service: Service for topological sorting
            cache_service: Cache service for performance optimization
        """
        self._build_repository = build_repository
        self._task_repository = task_repository
        self._topology_service = topology_service
        self._cache_service = cache_service

    async def get_build(self, name: str) -> Optional[Build]:
        """
        Retrieve single build by name with caching.
        
        Args:
            name: Build name to retrieve
            
        Returns:
            Build entity if found, None otherwise
        """
        if self._cache_service:
            cached_build = await self._cache_service.get_build(name)
            if cached_build:
                return cached_build
        
        build = await self._build_repository.get_build(name)
        
        if build and self._cache_service:
            await self._cache_service.cache_build(build)
        
        return build

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
        
        return await self._build_repository.get_builds(names)

    async def get_all_builds(self) -> Dict[str, Build]:
        """
        Retrieve all available builds.
        
        Returns:
            Dictionary mapping build names to Build entities
        """
        return await self._build_repository.get_all_builds()

    async def create_build(self, build: Build) -> Build:
        """
        Create new build with comprehensive validation.
        
        Args:
            build: Build entity to create
            
        Returns:
            Created build entity
            
        Raises:
            TaskNotFoundException: If build references non-existent tasks
            CircularDependencyException: If circular dependencies detected
        """
        tasks = await self._task_repository.get_tasks(build.tasks)
        missing_tasks = set(build.tasks) - set(tasks.keys())
        if missing_tasks:
            raise TaskNotFoundException(f"Missing tasks: {', '.join(missing_tasks)}")
        
        cycles = self._topology_service.detect_cycles(tasks)
        if cycles:
            raise CircularDependencyException(cycles[0])
        
        missing_deps = self._topology_service.validate_dependencies(build, tasks)
        if missing_deps:
            raise TaskNotFoundException(f"Missing dependencies: {', '.join(missing_deps)}")
        
        return await self._build_repository.save_build(build)

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
            CircularDependencyException: If circular dependencies detected
        """
        existing_build = await self._build_repository.get_build(build.name)
        if not existing_build:
            raise BuildNotFoundException(f"Build '{build.name}' not found")
        
        tasks = await self._task_repository.get_tasks(build.tasks)
        missing_tasks = set(build.tasks) - set(tasks.keys())
        if missing_tasks:
            raise TaskNotFoundException(f"Missing tasks: {', '.join(missing_tasks)}")
        
        cycles = self._topology_service.detect_cycles(tasks)
        if cycles:
            raise CircularDependencyException(cycles[0])
        
        missing_deps = self._topology_service.validate_dependencies(build, tasks)
        if missing_deps:
            raise TaskNotFoundException(f"Missing dependencies: {', '.join(missing_deps)}")
        
        return await self._build_repository.save_build(build)

    async def delete_build(self, name: str) -> bool:
        """
        Delete build by name.
        
        Args:
            name: Build name to delete
            
        Returns:
            True if build was deleted, False if not found
        """
        return await self._build_repository.delete_build(name)

    async def get_sorted_tasks(
        self,
        build_name: str,
        algorithm: Optional[SortAlgorithm] = None,
        use_cache: bool = True,
    ) -> SortedTaskList:
        """
        Get topologically sorted tasks for a build with intelligent caching.
        
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
        build = await self._build_repository.get_build(build_name)
        if not build:
            raise BuildNotFoundException(f"Build '{build_name}' not found")
        
        tasks = await self._task_repository.get_tasks(build.tasks)
        missing_tasks = set(build.tasks) - set(tasks.keys())
        if missing_tasks:
            raise TaskNotFoundException(f"Missing tasks: {', '.join(missing_tasks)}")
        
        if algorithm is None:
            algorithm = SortAlgorithm.KAHN
        
        if use_cache and self._cache_service:
            cached_result = await self._cache_service.get_sorted_tasks(
                build_name, algorithm, build, tasks
            )
            if cached_result:
                return cached_result
        
        sorted_tasks = await self._topology_service.sort_tasks(build, tasks, algorithm)
        
        if use_cache and self._cache_service:
            await self._cache_service.cache_sorted_tasks(
                sorted_tasks, algorithm, build, tasks
            )
        
        return sorted_tasks

    async def execute_build(
        self,
        build_name: str,
        algorithm: Optional[SortAlgorithm] = None,
    ) -> Build:
        """
        Execute build with topological task ordering.
        
        This is a simplified implementation for demonstration.
        In a real system, this would integrate with Celery for background processing.
        
        Args:
            build_name: Name of build to execute
            algorithm: Sorting algorithm to use for task ordering
            
        Returns:
            Updated build entity with execution results
            
        Raises:
            BuildNotFoundException: If build does not exist
            TaskNotFoundException: If build references non-existent tasks
            CircularDependencyException: If circular dependencies detected
        """
        build = await self._build_repository.get_build(build_name)
        if not build:
            raise BuildNotFoundException(f"Build '{build_name}' not found")
        
        updated_build = Build(
            name=build.name,
            tasks=build.tasks,
            status=BuildStatus.RUNNING,
            created_at=build.created_at,
        )
        await self._build_repository.save_build(updated_build)
        
        try:
            sorted_tasks = await self.get_sorted_tasks(build_name, algorithm, use_cache=False)
            
            tasks = await self._task_repository.get_tasks(build.tasks)
            executed_tasks = []
            
            for task_name in sorted_tasks.tasks:
                task = tasks[task_name]
                
                updated_task = Task(
                    name=task.name,
                    dependencies=task.dependencies,
                    status=TaskStatus.COMPLETED,
                    created_at=task.created_at,
                    error_message=None,
                )
                
                await self._task_repository.save_task(updated_task)
                executed_tasks.append(task_name)
            
            final_build = Build(
                name=build.name,
                tasks=build.tasks,
                status=BuildStatus.COMPLETED,
                created_at=build.created_at,
            )
            
            return await self._build_repository.save_build(final_build)
            
        except Exception as e:
            failed_build = Build(
                name=build.name,
                tasks=build.tasks,
                status=BuildStatus.FAILED,
                created_at=build.created_at,
            )
            
            await self._build_repository.save_build(failed_build)
            raise

    async def cancel_build(self, build_name: str) -> Build:
        """
        Cancel running build.
        
        Args:
            build_name: Name of build to cancel
            
        Returns:
            Updated build entity with cancelled status
            
        Raises:
            BuildNotFoundException: If build does not exist
        """
        build = await self._build_repository.get_build(build_name)
        if not build:
            raise BuildNotFoundException(f"Build '{build_name}' not found")
        
        cancelled_build = Build(
            name=build.name,
            tasks=build.tasks,
            status=BuildStatus.CANCELLED,
            created_at=build.created_at,
        )
        
        return await self._build_repository.save_build(cancelled_build)

    async def get_build_execution_status(self, build_name: str) -> Dict[str, TaskStatus]:
        """
        Get execution status of all tasks in a build.
        
        Args:
            build_name: Name of build to check
            
        Returns:
            Dictionary mapping task names to their current status
            
        Raises:
            BuildNotFoundException: If build does not exist
        """
        build = await self._build_repository.get_build(build_name)
        if not build:
            raise BuildNotFoundException(f"Build '{build_name}' not found")
        
        tasks = await self._task_repository.get_tasks(build.tasks)
        return {name: task.status for name, task in tasks.items()}

    async def reload_builds_from_config(self) -> int:
        """
        Reload builds from configuration files.
        
        This would integrate with ConfigurationService in a complete implementation.
        
        Returns:
            Number of builds loaded
        """
        return 0

    async def validate_build_dependencies(
        self, build_name: str
    ) -> tuple[bool, List[str]]:
        """
        Validate all dependencies for a build are satisfied.
        
        Args:
            build_name: Name of build to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
            
        Raises:
            BuildNotFoundException: If build does not exist
        """
        build = await self._build_repository.get_build(build_name)
        if not build:
            raise BuildNotFoundException(f"Build '{build_name}' not found")
        
        tasks = await self._task_repository.get_tasks(build.tasks)
        missing_deps = self._topology_service.validate_dependencies(build, tasks)
        
        cycles = self._topology_service.detect_cycles(tasks)
        cycle_issues = [f"Circular dependency: {' -> '.join(cycle)}" for cycle in cycles]
        
        all_issues = missing_deps + cycle_issues
        return len(all_issues) == 0, all_issues

    async def get_topological_sort(self, build_name: str) -> SortedTaskList:
        """
        Get topological sort for a build.
        
        Args:
            build_name: Name of build to sort
            
        Returns:
            SortedTaskList: Result of topological sort
            
        Raises:
            BuildNotFoundException: If build does not exist
            CircularDependencyException: If circular dependencies detected
        """
        build = await self._build_repository.get_build(build_name)
        if not build:
            raise BuildNotFoundException(f"Build '{build_name}' not found")
        
        # Get all tasks, not just build tasks - needed for dependency validation
        all_tasks = await self._task_repository.get_all_tasks()
        tasks = all_tasks
        
        cycles = self._topology_service.detect_cycles(tasks)
        if cycles:
            raise CircularDependencyException(f"Circular dependencies detected: {cycles}")
        
        sorted_result = await self._topology_service.sort_tasks(build, tasks)
        return sorted_result

    async def load_initial_data(self) -> None:
        """
        Load initial data from YAML configuration files.
        """
        try:
            # Load tasks
            tasks_path = "config/tasks.yaml"
            if os.path.exists(tasks_path):
                with open(tasks_path, "r", encoding="utf-8") as f:
                    tasks_data = yaml.safe_load(f)
                    
                for task_data in tasks_data.get("tasks", []):
                    task = Task(
                        name=task_data["name"],
                        dependencies=task_data.get("dependencies", []),
                        status=TaskStatus.PENDING,
                        created_at=datetime.now(),
                    )
                    await self._task_repository.save_task(task)
            
            # Load builds
            builds_path = "config/builds.yaml"
            if os.path.exists(builds_path):
                with open(builds_path, "r", encoding="utf-8") as f:
                    builds_data = yaml.safe_load(f)
                    
                for build_data in builds_data.get("builds", []):
                    build = Build(
                        name=build_data["name"],
                        tasks=build_data.get("tasks", []),
                        status=BuildStatus.PENDING,
                        created_at=datetime.now(),
                    )
                    await self._build_repository.save_build(build)
                    
        except Exception as e:
            print(f"Warning: Could not load initial data: {e}")

    async def detect_cycles(self, build_name: str) -> List[List[str]]:
        """
        Detect cycles in build dependencies.
        
        Args:
            build_name: Name of build to analyze
            
        Returns:
            List of cycles found (empty if no cycles)
            
        Raises:
            BuildNotFoundException: If build does not exist
        """
        build = await self._build_repository.get_build(build_name)
        if not build:
            raise BuildNotFoundException(f"Build '{build_name}' not found")
        
        tasks = await self._task_repository.get_tasks(build.tasks)
        return self._topology_service.detect_cycles(tasks)