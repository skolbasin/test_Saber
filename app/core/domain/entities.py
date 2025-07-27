"""Domain entities for the build system."""

from dataclasses import dataclass
from typing import List, Optional, Set
from datetime import datetime

from .enums import TaskStatus, BuildStatus


@dataclass(frozen=True)
class Task:
    """
    Task entity representing a single build task.
    
    Attributes:
        name: Unique task identifier
        dependencies: Set of task names this task depends on
        status: Current execution status
        created_at: Task creation timestamp
        updated_at: Last update timestamp
        error_message: Error details if task failed
    """
    
    name: str
    dependencies: Set[str]
    status: TaskStatus = TaskStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate task data after initialization."""
        if not self.name:
            raise ValueError("Task name cannot be empty")
        if self.name in self.dependencies:
            raise ValueError("Task cannot depend on itself")

    def has_dependencies(self) -> bool:
        """Check if task has any dependencies."""
        return len(self.dependencies) > 0

    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """
        Check if task can be executed based on completed dependencies.
        
        Args:
            completed_tasks: Set of completed task names
            
        Returns:
            True if all dependencies are completed
        """
        return self.dependencies.issubset(completed_tasks)


@dataclass(frozen=True)
class Build:
    """
    Build entity representing a collection of tasks.
    
    Attributes:
        name: Unique build identifier
        tasks: List of task names in this build
        status: Current build status
        created_at: Build creation timestamp
        updated_at: Last update timestamp
        error_message: Error details if build failed
    """
    
    name: str
    tasks: List[str]
    status: BuildStatus = BuildStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate build data after initialization."""
        if not self.name:
            raise ValueError("Build name cannot be empty")
        if not self.tasks:
            raise ValueError("Build must contain at least one task")
        if len(self.tasks) != len(set(self.tasks)):
            raise ValueError("Build cannot contain duplicate tasks")

    def get_task_count(self) -> int:
        """Get total number of tasks in build."""
        return len(self.tasks)


@dataclass(frozen=True)
class SortedTaskList:
    """
    Result of topological sorting operation.
    
    Attributes:
        build_name: Name of the build that was sorted
        tasks: Topologically sorted list of task names
        algorithm_used: Algorithm used for sorting
        execution_time_ms: Time taken for sorting in milliseconds
        has_cycles: Whether circular dependencies were detected
        cycle_details: Details about detected cycles if any
    """
    
    build_name: str
    tasks: List[str]
    algorithm_used: str
    execution_time_ms: float
    has_cycles: bool = False
    cycle_details: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Validate sorted task list data."""
        if not self.build_name:
            raise ValueError("Build name cannot be empty")
        if self.has_cycles and not self.cycle_details:
            raise ValueError("Cycle details required when cycles detected")
        if self.execution_time_ms < 0:
            raise ValueError("Execution time cannot be negative")