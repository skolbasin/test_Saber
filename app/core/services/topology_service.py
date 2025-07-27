"""Topological sorting service implementation."""

import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set

from app.core.domain.entities import Build, SortedTaskList, Task
from app.core.domain.enums import SortAlgorithm
from app.core.exceptions import (
    CircularDependencyException,
    TaskNotFoundException,
    TopologicalSortException,
)
from .interfaces import TopologyServiceInterface


class TopologyService(TopologyServiceInterface):
    """
    High-performance topological sorting service.
    
    Implements both Kahn's algorithm and DFS-based topological sorting
    with cycle detection and comprehensive error handling for build systems.
    """

    async def sort_tasks(
        self,
        build: Build,
        tasks: Dict[str, Task],
        algorithm: Optional[SortAlgorithm] = None,
    ) -> SortedTaskList:
        """
        Sort tasks in topological order based on dependencies.
        
        Uses Kahn's algorithm by default for optimal performance with
        early cycle detection and clear error reporting.
        
        Args:
            build: Build entity containing task names
            tasks: Dictionary mapping task names to Task entities
            algorithm: Sorting algorithm to use (defaults to Kahn)
            
        Returns:
            Sorted task list with execution metadata
            
        Raises:
            CircularDependencyException: If circular dependencies detected
            TaskNotFoundException: If build references non-existent tasks
            TopologicalSortException: If sorting fails for other reasons
        """
        start_time = time.perf_counter()
        
        if algorithm is None:
            algorithm = SortAlgorithm.KAHN
            
        missing_dependencies = self.validate_dependencies(build, tasks)
        if missing_dependencies:
            raise TaskNotFoundException(f"Missing tasks: {', '.join(missing_dependencies)}")
        
        try:
            if algorithm == SortAlgorithm.KAHN:
                sorted_tasks = await self._kahn_sort(build, tasks)
            else:
                sorted_tasks = await self._dfs_sort(build, tasks)
                
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return SortedTaskList(
                build_name=build.name,
                tasks=sorted_tasks,
                algorithm_used=algorithm.value,
                execution_time_ms=execution_time,
                has_cycles=False,
            )
            
        except CircularDependencyException:
            raise
        except Exception as e:
            raise TopologicalSortException(
                build.name, f"Sorting failed with {algorithm.value}: {e}"
            )

    def detect_cycles(self, tasks: Dict[str, Task]) -> List[List[str]]:
        """
        Detect circular dependencies using DFS with comprehensive cycle reporting.
        
        Args:
            tasks: Dictionary mapping task names to Task entities
            
        Returns:
            List of cycles, where each cycle is a list of task names
        """
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs_cycle_detection(task_name: str, path: List[str]) -> None:
            if task_name in rec_stack:
                cycle_start = path.index(task_name)
                cycle = path[cycle_start:] + [task_name]
                cycles.append(cycle)
                return
                
            if task_name in visited:
                return
                
            visited.add(task_name)
            rec_stack.add(task_name)
            path.append(task_name)
            
            task = tasks.get(task_name)
            if task:
                for dep in task.dependencies:
                    if dep in tasks:
                        dfs_cycle_detection(dep, path[:])
            
            rec_stack.remove(task_name)
            path.pop()
        
        for task_name in tasks:
            if task_name not in visited:
                dfs_cycle_detection(task_name, [])
        
        return cycles

    def validate_dependencies(
        self, build: Build, tasks: Dict[str, Task]
    ) -> List[str]:
        """
        Validate that all task dependencies exist in the task collection.
        
        Args:
            build: Build entity to validate
            tasks: Available tasks dictionary
            
        Returns:
            List of missing dependency names (empty if all valid)
        """
        missing_deps = []
        build_tasks = set(build.tasks)
        
        for task_name in build.tasks:
            if task_name not in tasks:
                missing_deps.append(task_name)
                continue
                
            task = tasks[task_name]
            if not hasattr(task, 'dependencies'):
                missing_deps.append(f"Invalid task object: {task_name}")
                continue
                
            for dep in task.dependencies:
                if dep not in tasks:
                    missing_deps.append(dep)
        
        return list(set(missing_deps))

    async def _kahn_sort(self, build: Build, tasks: Dict[str, Task]) -> List[str]:
        """
        Kahn's algorithm implementation for topological sorting.
        
        Optimal for sparse graphs with early cycle detection and
        excellent performance characteristics for build systems.
        
        Args:
            build: Build entity containing task names
            tasks: Dictionary mapping task names to Task entities
            
        Returns:
            Topologically sorted list of task names
            
        Raises:
            CircularDependencyException: If circular dependencies detected
        """
        build_tasks = set(build.tasks)
        in_degree = defaultdict(int)
        graph = defaultdict(set)
        
        for task_name in build.tasks:
            task = tasks[task_name]
            build_deps = task.dependencies.intersection(build_tasks)
            in_degree[task_name] = len(build_deps)
            
            for dep in build_deps:
                graph[dep].add(task_name)
        
        queue = deque([task for task in build.tasks if in_degree[task] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(build.tasks):
            remaining_tasks = set(build.tasks) - set(result)
            cycles = self._find_cycles_in_subgraph(remaining_tasks, tasks)
            if cycles:
                raise CircularDependencyException(cycles[0])
            else:
                raise TopologicalSortException(
                    build.name, f"Unable to sort {len(remaining_tasks)} tasks"
                )
        
        return result

    async def _dfs_sort(self, build: Build, tasks: Dict[str, Task]) -> List[str]:
        """
        DFS-based topological sorting implementation.
        
        Uses post-order traversal for topological ordering with
        comprehensive cycle detection during traversal.
        
        Args:
            build: Build entity containing task names
            tasks: Dictionary mapping task names to Task entities
            
        Returns:
            Topologically sorted list of task names
            
        Raises:
            CircularDependencyException: If circular dependencies detected
        """
        build_tasks = set(build.tasks)
        visited = set()
        rec_stack = set()
        result = []
        
        def dfs_visit(task_name: str, path: List[str]) -> None:
            if task_name in rec_stack:
                cycle_start = path.index(task_name)
                cycle = path[cycle_start:] + [task_name]
                raise CircularDependencyException(cycle)
            
            if task_name in visited:
                return
            
            visited.add(task_name)
            rec_stack.add(task_name)
            path.append(task_name)
            
            task = tasks[task_name]
            build_deps = task.dependencies.intersection(build_tasks)
            
            for dep in build_deps:
                dfs_visit(dep, path[:])
            
            rec_stack.remove(task_name)
            path.pop()
            result.append(task_name)
        
        for task_name in build.tasks:
            if task_name not in visited:
                dfs_visit(task_name, [])
        
        return list(reversed(result))

    def _find_cycles_in_subgraph(
        self, task_names: Set[str], tasks: Dict[str, Task]
    ) -> List[List[str]]:
        """
        Find cycles within a specific subset of tasks.
        
        Used by Kahn's algorithm to provide detailed cycle information
        when sorting fails due to circular dependencies.
        
        Args:
            task_names: Set of task names to check for cycles
            tasks: Full tasks dictionary
            
        Returns:
            List of detected cycles
        """
        subgraph_tasks = {name: tasks[name] for name in task_names if name in tasks}
        return self.detect_cycles(subgraph_tasks)