"""YAML configuration loader utility."""

import asyncio
from pathlib import Path
from typing import Any, Dict

import yaml

from app.core.exceptions import ConfigurationException


class YamlLoader:
    """
    Asynchronous YAML configuration loader with validation.
    
    Provides safe YAML loading with comprehensive error handling
    and validation for build system configuration files.
    """

    @staticmethod
    async def load_yaml_file(file_path: str) -> Dict[str, Any]:
        """
        Load YAML file asynchronously with error handling.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Parsed YAML content as dictionary
            
        Raises:
            ConfigurationException: If file cannot be loaded or parsed
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise ConfigurationException(
                    "file", f"Configuration file not found: {file_path}"
                )
            
            if not path.is_file():
                raise ConfigurationException(
                    "file", f"Path is not a file: {file_path}"
                )
            
            content = await asyncio.to_thread(YamlLoader._read_file_sync, str(path))
            
            if not content.strip():
                return {}
            
            try:
                data = yaml.safe_load(content)
                if data is None:
                    return {}
                
                if not isinstance(data, dict):
                    raise ConfigurationException(
                        "yaml", f"Root element must be a dictionary in {file_path}"
                    )
                
                return data
                
            except yaml.YAMLError as e:
                raise ConfigurationException(
                    "yaml", f"Invalid YAML syntax in {file_path}: {e}"
                )
                
        except ConfigurationException:
            raise
        except Exception as e:
            raise ConfigurationException(
                "file", f"Failed to load {file_path}: {e}"
            )

    @staticmethod
    def _read_file_sync(file_path: str) -> str:
        """
        Synchronous file reading for thread pool execution.
        
        Args:
            file_path: Path to file
            
        Returns:
            File contents as string
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    async def validate_yaml_structure(
        data: Dict[str, Any], 
        required_keys: list[str],
        file_path: str
    ) -> None:
        """
        Validate YAML structure has required keys.
        
        Args:
            data: Parsed YAML data
            required_keys: List of required top-level keys
            file_path: File path for error reporting
            
        Raises:
            ConfigurationException: If structure is invalid
        """
        for key in required_keys:
            if key not in data:
                raise ConfigurationException(
                    "structure", 
                    f"Missing required key '{key}' in {file_path}"
                )

    @staticmethod
    async def validate_tasks_structure(data: Dict[str, Any], file_path: str) -> None:
        """
        Validate tasks YAML structure.
        
        Args:
            data: Parsed YAML data
            file_path: File path for error reporting
            
        Raises:
            ConfigurationException: If structure is invalid
        """
        await YamlLoader.validate_yaml_structure(data, ["tasks"], file_path)
        
        tasks = data["tasks"]
        if not isinstance(tasks, list):
            raise ConfigurationException(
                "structure", f"'tasks' must be a list in {file_path}"
            )
        
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                raise ConfigurationException(
                    "structure", f"Task {i} must be a dictionary in {file_path}"
                )
            
            if "name" not in task:
                raise ConfigurationException(
                    "structure", f"Task {i} missing 'name' field in {file_path}"
                )
            
            if not isinstance(task["name"], str) or not task["name"].strip():
                raise ConfigurationException(
                    "structure", f"Task {i} name must be non-empty string in {file_path}"
                )
            
            if "dependencies" in task:
                deps = task["dependencies"]
                if not isinstance(deps, list):
                    raise ConfigurationException(
                        "structure", 
                        f"Task '{task['name']}' dependencies must be a list in {file_path}"
                    )
                
                for dep in deps:
                    if not isinstance(dep, str) or not dep.strip():
                        raise ConfigurationException(
                            "structure",
                            f"Task '{task['name']}' dependency must be non-empty string in {file_path}"
                        )

    @staticmethod
    async def validate_builds_structure(data: Dict[str, Any], file_path: str) -> None:
        """
        Validate builds YAML structure.
        
        Args:
            data: Parsed YAML data
            file_path: File path for error reporting
            
        Raises:
            ConfigurationException: If structure is invalid
        """
        await YamlLoader.validate_yaml_structure(data, ["builds"], file_path)
        
        builds = data["builds"]
        if not isinstance(builds, list):
            raise ConfigurationException(
                "structure", f"'builds' must be a list in {file_path}"
            )
        
        for i, build in enumerate(builds):
            if not isinstance(build, dict):
                raise ConfigurationException(
                    "structure", f"Build {i} must be a dictionary in {file_path}"
                )
            
            if "name" not in build:
                raise ConfigurationException(
                    "structure", f"Build {i} missing 'name' field in {file_path}"
                )
            
            if not isinstance(build["name"], str) or not build["name"].strip():
                raise ConfigurationException(
                    "structure", f"Build {i} name must be non-empty string in {file_path}"
                )
            
            if "tasks" not in build:
                raise ConfigurationException(
                    "structure", f"Build '{build['name']}' missing 'tasks' field in {file_path}"
                )
            
            tasks = build["tasks"]
            if not isinstance(tasks, list):
                raise ConfigurationException(
                    "structure", 
                    f"Build '{build['name']}' tasks must be a list in {file_path}"
                )
            
            if not tasks:
                raise ConfigurationException(
                    "structure",
                    f"Build '{build['name']}' must contain at least one task in {file_path}"
                )
            
            for task in tasks:
                if not isinstance(task, str) or not task.strip():
                    raise ConfigurationException(
                        "structure",
                        f"Build '{build['name']}' task must be non-empty string in {file_path}"
                    )