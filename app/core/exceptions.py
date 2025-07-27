"""Domain exceptions for the build system."""

from typing import List, Optional


class DomainException(Exception):
    """Base exception for domain-related errors."""
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        """
        Initialize domain exception.
        
        Args:
            message: Human-readable error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details


class TaskNotFoundException(DomainException):
    """Raised when a task is not found."""
    
    def __init__(self, task_name_or_message: str) -> None:
        """
        Initialize task not found exception.
        
        Args:
            task_name_or_message: Name of the missing task or custom message
        """
        if task_name_or_message.startswith("Missing tasks:") or task_name_or_message.startswith("Missing dependencies:"):
            message = task_name_or_message
            super().__init__(message, task_name_or_message)
            self.task_name = None
        else:
            message = f"Task '{task_name_or_message}' not found"
            super().__init__(message, f"Task name: {task_name_or_message}")
            self.task_name = task_name_or_message


class BuildNotFoundException(DomainException):
    """Raised when a build is not found."""
    
    def __init__(self, build_name: str) -> None:
        """
        Initialize build not found exception.
        
        Args:
            build_name: Name of the missing build
        """
        message = f"Build '{build_name}' not found"
        super().__init__(message, f"Build name: {build_name}")
        self.build_name = build_name


class CircularDependencyException(DomainException):
    """Raised when circular dependencies are detected."""
    
    def __init__(self, cycle: List[str]) -> None:
        """
        Initialize circular dependency exception.
        
        Args:
            cycle: List of task names forming the cycle
        """
        cycle_str = " -> ".join(cycle + [cycle[0]])
        message = f"Circular dependency detected: {cycle_str}"
        super().__init__(message, f"Cycle: {cycle}")
        self.cycle = cycle


class InvalidTaskDependencyException(DomainException):
    """Raised when a task has invalid dependencies."""
    
    def __init__(self, task_name: str, invalid_dependencies: List[str]) -> None:
        """
        Initialize invalid task dependency exception.
        
        Args:
            task_name: Name of the task with invalid dependencies
            invalid_dependencies: List of invalid dependency names
        """
        deps_str = ", ".join(invalid_dependencies)
        message = f"Task '{task_name}' has invalid dependencies: {deps_str}"
        super().__init__(message, f"Task: {task_name}, Invalid deps: {invalid_dependencies}")
        self.task_name = task_name
        self.invalid_dependencies = invalid_dependencies


class ConfigurationException(DomainException):
    """Raised when configuration is invalid."""
    
    def __init__(self, config_type: str, details: str) -> None:
        """
        Initialize configuration exception.
        
        Args:
            config_type: Type of configuration (tasks, builds)
            details: Specific configuration error details
        """
        message = f"Invalid {config_type} configuration: {details}"
        super().__init__(message, details)
        self.config_type = config_type


class TopologicalSortException(DomainException):
    """Raised when topological sorting fails."""
    
    def __init__(self, build_name: str, reason: str) -> None:
        """
        Initialize topological sort exception.
        
        Args:
            build_name: Name of the build being sorted
            reason: Specific reason for sort failure
        """
        message = f"Failed to sort build '{build_name}': {reason}"
        super().__init__(message, f"Build: {build_name}, Reason: {reason}")
        self.build_name = build_name
        self.reason = reason