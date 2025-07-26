"""Cache service implementation for build system."""

import hashlib
import json
from typing import Any, Dict, Optional
from datetime import timedelta

from app.core.domain.entities import Build, SortedTaskList, Task
from app.core.domain.enums import SortAlgorithm
from .redis_client import RedisClient


class CacheService:
    """
    High-performance cache service for build system operations.
    
    Provides intelligent caching for topological sort results, build configurations,
    and task data with automatic invalidation and optimized cache keys.
    """

    def __init__(self, redis_client: RedisClient):
        """
        Initialize cache service.
        
        Args:
            redis_client: Redis client instance
        """
        self._redis = redis_client

    def _build_cache_key(self, build_name: str) -> str:
        """Generate cache key for build."""
        return f"build:{build_name}"

    def _task_cache_key(self, task_name: str) -> str:
        """Generate cache key for task."""
        return f"task:{task_name}"

    def _sorted_tasks_cache_key(
        self, build_name: str, algorithm: SortAlgorithm, config_hash: str
    ) -> str:
        """Generate cache key for sorted tasks."""
        return f"sorted:{build_name}:{algorithm.value}:{config_hash}"

    def _user_session_key(self, user_id: int) -> str:
        """Generate cache key for user session."""
        return f"session:user:{user_id}"

    def _build_status_key(self, build_name: str) -> str:
        """Generate cache key for build status."""
        return f"status:build:{build_name}"

    def _config_hash(self, build: Build, tasks: Dict[str, Task]) -> str:
        """
        Generate configuration hash for cache invalidation.
        
        Args:
            build: Build entity
            tasks: Tasks dictionary
            
        Returns:
            MD5 hash of configuration
        """
        config_data = {
            "build_tasks": sorted(build.tasks),
            "task_dependencies": {
                name: sorted(list(task.dependencies))
                for name, task in sorted(tasks.items())
            },
        }
        
        config_str = json.dumps(config_data, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    async def get_sorted_tasks(
        self,
        build_name: str,
        algorithm: SortAlgorithm,
        build: Build,
        tasks: Dict[str, Task],
    ) -> Optional[SortedTaskList]:
        """
        Get cached sorted tasks result.
        
        Args:
            build_name: Build name
            algorithm: Sorting algorithm
            build: Build entity
            tasks: Tasks dictionary
            
        Returns:
            Cached SortedTaskList or None if not found/invalid
        """
        config_hash = self._config_hash(build, tasks)
        cache_key = self._sorted_tasks_cache_key(build_name, algorithm, config_hash)
        
        cached_data = await self._redis.get(cache_key)
        if cached_data:
            try:
                return SortedTaskList(
                    build_name=cached_data["build_name"],
                    tasks=cached_data["tasks"],
                    algorithm_used=cached_data["algorithm_used"],
                    execution_time_ms=cached_data["execution_time_ms"],
                    has_cycles=cached_data["has_cycles"],
                    cycle_details=cached_data.get("cycle_details"),
                )
            except (KeyError, TypeError):
                await self._redis.delete(cache_key)
        
        return None

    async def cache_sorted_tasks(
        self,
        sorted_tasks: SortedTaskList,
        algorithm: SortAlgorithm,
        build: Build,
        tasks: Dict[str, Task],
        ttl: timedelta = timedelta(hours=1),
    ) -> bool:
        """
        Cache sorted tasks result.
        
        Args:
            sorted_tasks: Sorted tasks result
            algorithm: Sorting algorithm used
            build: Build entity
            tasks: Tasks dictionary
            ttl: Cache time-to-live
            
        Returns:
            True if cached successfully, False otherwise
        """
        config_hash = self._config_hash(build, tasks)
        cache_key = self._sorted_tasks_cache_key(
            sorted_tasks.build_name, algorithm, config_hash
        )
        
        cache_data = {
            "build_name": sorted_tasks.build_name,
            "tasks": sorted_tasks.tasks,
            "algorithm_used": sorted_tasks.algorithm_used,
            "execution_time_ms": sorted_tasks.execution_time_ms,
            "has_cycles": sorted_tasks.has_cycles,
            "cycle_details": sorted_tasks.cycle_details,
        }
        
        return await self._redis.set(cache_key, cache_data, ttl)

    async def get_build(self, build_name: str) -> Optional[Build]:
        """
        Get cached build.
        
        Args:
            build_name: Build name
            
        Returns:
            Cached Build or None if not found
        """
        cache_key = self._build_cache_key(build_name)
        cached_data = await self._redis.get(cache_key)
        
        if cached_data:
            try:
                return Build(
                    name=cached_data["name"],
                    tasks=cached_data["tasks"],
                    status=cached_data["status"],
                    created_at=cached_data.get("created_at"),
                    updated_at=cached_data.get("updated_at"),
                    error_message=cached_data.get("error_message"),
                )
            except (KeyError, TypeError):
                await self._redis.delete(cache_key)
        
        return None

    async def cache_build(
        self, build: Build, ttl: timedelta = timedelta(minutes=30)
    ) -> bool:
        """
        Cache build entity.
        
        Args:
            build: Build to cache
            ttl: Cache time-to-live
            
        Returns:
            True if cached successfully, False otherwise
        """
        cache_key = self._build_cache_key(build.name)
        
        cache_data = {
            "name": build.name,
            "tasks": build.tasks,
            "status": build.status.value,
            "created_at": build.created_at.isoformat() if build.created_at else None,
            "updated_at": build.updated_at.isoformat() if build.updated_at else None,
            "error_message": build.error_message,
        }
        
        return await self._redis.set(cache_key, cache_data, ttl)

    async def get_task(self, task_name: str) -> Optional[Task]:
        """
        Get cached task.
        
        Args:
            task_name: Task name
            
        Returns:
            Cached Task or None if not found
        """
        cache_key = self._task_cache_key(task_name)
        cached_data = await self._redis.get(cache_key)
        
        if cached_data:
            try:
                return Task(
                    name=cached_data["name"],
                    dependencies=set(cached_data["dependencies"]),
                    status=cached_data["status"],
                    created_at=cached_data.get("created_at"),
                    updated_at=cached_data.get("updated_at"),
                    error_message=cached_data.get("error_message"),
                )
            except (KeyError, TypeError):
                await self._redis.delete(cache_key)
        
        return None

    async def cache_task(
        self, task: Task, ttl: timedelta = timedelta(minutes=15)
    ) -> bool:
        """
        Cache task entity.
        
        Args:
            task: Task to cache
            ttl: Cache time-to-live
            
        Returns:
            True if cached successfully, False otherwise
        """
        cache_key = self._task_cache_key(task.name)
        
        cache_data = {
            "name": task.name,
            "dependencies": list(task.dependencies),
            "status": task.status.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "error_message": task.error_message,
        }
        
        return await self._redis.set(cache_key, cache_data, ttl)

    async def invalidate_build(self, build_name: str) -> bool:
        """
        Invalidate all cache entries for a build.
        
        Args:
            build_name: Build name
            
        Returns:
            True if invalidated successfully
        """
        build_deleted = await self._redis.delete(self._build_cache_key(build_name))
        
        pattern = f"sorted:{build_name}:*"
        sorted_deleted = await self._redis.clear_pattern(pattern)
        
        status_deleted = await self._redis.delete(self._build_status_key(build_name))
        
        return build_deleted or sorted_deleted > 0 or status_deleted

    async def invalidate_task(self, task_name: str) -> bool:
        """
        Invalidate cache entries for a task and related builds.
        
        Args:
            task_name: Task name
            
        Returns:
            True if invalidated successfully
        """
        task_deleted = await self._redis.delete(self._task_cache_key(task_name))
        
        sorted_deleted = await self._redis.clear_pattern("sorted:*")
        
        return task_deleted or sorted_deleted > 0

    async def set_user_session(
        self, user_id: int, session_data: Dict[str, Any], ttl: timedelta = timedelta(hours=24)
    ) -> bool:
        """
        Set user session data.
        
        Args:
            user_id: User ID
            session_data: Session data
            ttl: Session time-to-live
            
        Returns:
            True if set successfully
        """
        cache_key = self._user_session_key(user_id)
        return await self._redis.set(cache_key, session_data, ttl)

    async def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user session data.
        
        Args:
            user_id: User ID
            
        Returns:
            Session data or None if not found
        """
        cache_key = self._user_session_key(user_id)
        return await self._redis.get(cache_key)

    async def delete_user_session(self, user_id: int) -> bool:
        """
        Delete user session.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully
        """
        cache_key = self._user_session_key(user_id)
        return await self._redis.delete(cache_key)

    async def set_build_status(
        self, build_name: str, status_data: Dict[str, Any], ttl: timedelta = timedelta(minutes=5)
    ) -> bool:
        """
        Cache build execution status.
        
        Args:
            build_name: Build name
            status_data: Status information
            ttl: Cache time-to-live
            
        Returns:
            True if cached successfully
        """
        cache_key = self._build_status_key(build_name)
        return await self._redis.set(cache_key, status_data, ttl)

    async def get_build_status(self, build_name: str) -> Optional[Dict[str, Any]]:
        """
        Get cached build execution status.
        
        Args:
            build_name: Build name
            
        Returns:
            Status data or None if not found
        """
        cache_key = self._build_status_key(build_name)
        return await self._redis.get(cache_key)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform cache health check.
        
        Returns:
            Health status information
        """
        try:
            is_connected = await self._redis.ping()
            info = await self._redis.get_info() if is_connected else {}
            
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }

    async def clear_all_cache(self) -> bool:
        """
        Clear all cache entries (use with caution).
        
        Returns:
            True if cleared successfully
        """
        try:
            patterns = ["build:*", "task:*", "sorted:*", "session:*", "status:*"]
            total_deleted = 0
            
            for pattern in patterns:
                deleted = await self._redis.clear_pattern(pattern)
                total_deleted += deleted
            
            return total_deleted > 0
        except Exception:
            return False