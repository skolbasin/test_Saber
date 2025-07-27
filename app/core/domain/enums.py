"""Domain enums for the build system."""

from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status enumeration."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BuildStatus(str, Enum):
    """Build execution status enumeration."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SortAlgorithm(str, Enum):
    """Topological sorting algorithm types."""
    
    KAHN = "kahn"
    DFS = "dfs"