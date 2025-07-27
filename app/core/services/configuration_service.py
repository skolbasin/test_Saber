"""Configuration management service implementation."""

from typing import Dict, List

from app.core.domain.entities import Build, Task
from app.core.domain.enums import TaskStatus, BuildStatus
from app.core.exceptions import ConfigurationException
from app.utils.yaml_loader import YamlLoader
from .interfaces import ConfigurationServiceInterface


class ConfigurationService(ConfigurationServiceInterface):
    """
    YAML configuration management service.
    
    Handles loading, parsing, and validation of tasks and builds
    configuration files with comprehensive error reporting.
    """

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
        try:
            data = await YamlLoader.load_yaml_file(file_path)
            
            if not data:
                return {}
            
            await YamlLoader.validate_tasks_structure(data, file_path)
            
            tasks = {}
            task_names = set()
            
            for task_data in data["tasks"]:
                task_name = task_data["name"]
                
                if task_name in task_names:
                    raise ConfigurationException(
                        "tasks", f"Duplicate task name '{task_name}' in {file_path}"
                    )
                
                task_names.add(task_name)
                
                dependencies = set(task_data.get("dependencies", []))
                
                if task_name in dependencies:
                    raise ConfigurationException(
                        "tasks", f"Task '{task_name}' cannot depend on itself in {file_path}"
                    )
                
                task = Task(
                    name=task_name,
                    dependencies=dependencies,
                    status=TaskStatus.PENDING,
                )
                
                tasks[task_name] = task
            
            self._validate_task_dependencies(tasks, file_path)
            
            return tasks
            
        except ConfigurationException:
            raise
        except Exception as e:
            raise ConfigurationException(
                "tasks", f"Failed to load tasks from {file_path}: {e}"
            )

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
        try:
            data = await YamlLoader.load_yaml_file(file_path)
            
            if not data:
                return {}
            
            await YamlLoader.validate_builds_structure(data, file_path)
            
            builds = {}
            build_names = set()
            
            for build_data in data["builds"]:
                build_name = build_data["name"]
                
                if build_name in build_names:
                    raise ConfigurationException(
                        "builds", f"Duplicate build name '{build_name}' in {file_path}"
                    )
                
                build_names.add(build_name)
                
                tasks = build_data["tasks"]
                
                if len(tasks) != len(set(tasks)):
                    raise ConfigurationException(
                        "builds", f"Build '{build_name}' contains duplicate tasks in {file_path}"
                    )
                
                build = Build(
                    name=build_name,
                    tasks=tasks,
                    status=BuildStatus.PENDING,
                )
                
                builds[build_name] = build
            
            return builds
            
        except ConfigurationException:
            raise
        except Exception as e:
            raise ConfigurationException(
                "builds", f"Failed to load builds from {file_path}: {e}"
            )

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
        errors = []
        
        try:
            self._validate_task_dependencies(tasks, "tasks configuration")
        except ConfigurationException as e:
            errors.append(e.message)
        
        for build_name, build in builds.items():
            missing_tasks = []
            for task_name in build.tasks:
                if task_name not in tasks:
                    missing_tasks.append(task_name)
            
            if missing_tasks:
                errors.append(
                    f"Build '{build_name}' references non-existent tasks: {', '.join(missing_tasks)}"
                )
        
        return errors

    async def reload_all_configuration(self) -> tuple[int, int]:
        """
        Reload all configuration from files.
        
        Returns:
            Tuple of (tasks_loaded, builds_loaded)
        """
        from app.config import get_settings
        settings = get_settings()
        
        tasks = await self.load_tasks_config(settings.tasks_config_path)
        builds = await self.load_builds_config(settings.builds_config_path)
        
        validation_errors = await self.validate_configuration(tasks, builds)
        if validation_errors:
            raise ConfigurationException(
                "validation", f"Configuration validation failed: {'; '.join(validation_errors)}"
            )
        
        return len(tasks), len(builds)

    def _validate_task_dependencies(self, tasks: Dict[str, Task], context: str) -> None:
        """
        Validate that all task dependencies exist within the task set.
        
        Args:
            tasks: Tasks dictionary to validate
            context: Context for error reporting
            
        Raises:
            ConfigurationException: If dependencies are invalid
        """
        task_names = set(tasks.keys())
        
        for task_name, task in tasks.items():
            missing_deps = task.dependencies - task_names
            if missing_deps:
                raise ConfigurationException(
                    "tasks",
                    f"Task '{task_name}' has invalid dependencies: {', '.join(missing_deps)} in {context}"
                )