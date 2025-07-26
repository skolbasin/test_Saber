"""Celery tasks for build execution and management."""

from datetime import datetime
from typing import Dict

from app.core.domain.entities import Build, Task
from app.core.domain.enums import BuildStatus, TaskStatus, SortAlgorithm
from app.core.exceptions import (
    BuildNotFoundException,
    TaskNotFoundException,
    CircularDependencyException,
)
from app.infrastructure.tasks.celery_app import celery_app
from app.utils.async_helpers import run_async


@celery_app.task(bind=True, max_retries=3)
def execute_build_async(self, build_name: str, algorithm: str = "kahn") -> Dict:
    """
    Execute build asynchronously with topological task ordering.
    
    Args:
        build_name: Name of build to execute
        algorithm: Sorting algorithm to use
        
    Returns:
        Build execution result
        
    Raises:
        Retry: If build execution should be retried
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "status": f"Starting build execution for {build_name}",
            },
        )
        
        result = run_async(_execute_build_internal(build_name, algorithm, self))
        
        return {
            "build_name": build_name,
            "status": "COMPLETED",
            "result": result,
            "completed_at": datetime.utcnow().isoformat(),
        }
        
    except CircularDependencyException as e:
        return {
            "build_name": build_name,
            "status": "FAILED",
            "error": f"Circular dependency detected: {e.message}",
            "failed_at": datetime.utcnow().isoformat(),
        }
        
    except (BuildNotFoundException, TaskNotFoundException) as e:
        return {
            "build_name": build_name,
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        
        return {
            "build_name": build_name,
            "status": "FAILED",
            "error": f"Build execution failed after {self.max_retries} retries: {str(exc)}",
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _execute_build_internal(build_name: str, algorithm: str, task_instance) -> Dict:
    """
    Internal async build execution logic.
    
    Args:
        build_name: Build name
        algorithm: Sorting algorithm
        task_instance: Celery task instance for progress updates
        
    Returns:
        Execution result dictionary
    """
    from app.core.services.build_service import BuildService
    from app.core.services.topology_service import TopologyService
    from app.infrastructure.database.repositories.build_repository import SqlBuildRepository
    from app.infrastructure.database.repositories.task_repository import SqlTaskRepository
    from app.infrastructure.database.session import get_session_maker
    from app.infrastructure.cache.cache_service import CacheService
    from app.infrastructure.cache.redis_client import get_redis_client
    
    sort_algorithm = SortAlgorithm.KAHN if algorithm == "kahn" else SortAlgorithm.DFS
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            build_repo = SqlBuildRepository(session)
            task_repo = SqlTaskRepository(session)
            topology_service = TopologyService()
            redis_client = get_redis_client()
            cache_service = CacheService(redis_client)
            build_service = BuildService(build_repo, task_repo, topology_service, cache_service)
            
            build = await build_service.get_build(build_name)
            if not build:
                raise BuildNotFoundException(f"Build '{build_name}' not found")
            
            build_running = Build(
                name=build.name,
                tasks=build.tasks,
                status=BuildStatus.RUNNING,
                created_at=build.created_at,
            )
            await build_repo.save_build(build_running)
            await session.commit()
            
            task_instance.update_state(
                state="PROGRESS",
                meta={
                    "current": 10,
                    "total": 100,
                    "status": f"Sorting tasks for {build_name}",
                },
            )
            
            sorted_tasks = await build_service.get_sorted_tasks(
                build_name, sort_algorithm, use_cache=False
            )
            
            tasks = await task_repo.get_tasks(build.tasks)
            total_tasks = len(sorted_tasks.tasks)
            executed_tasks = []
            
            for i, task_name in enumerate(sorted_tasks.tasks):
                task = tasks[task_name]
                
                progress = 10 + (i * 80 // total_tasks)
                task_instance.update_state(
                    state="PROGRESS",
                    meta={
                        "current": progress,
                        "total": 100,
                        "status": f"Executing task {task_name}",
                        "completed_tasks": executed_tasks,
                    },
                )
                
                await _execute_single_task(task, task_repo, session)
                executed_tasks.append(task_name)
            
            task_instance.update_state(
                state="PROGRESS",
                meta={
                    "current": 95,
                    "total": 100,
                    "status": f"Finalizing build {build_name}",
                },
            )
            
            build_completed = Build(
                name=build.name,
                tasks=build.tasks,
                status=BuildStatus.COMPLETED,
                created_at=build.created_at,
            )
            await build_repo.save_build(build_completed)
            await session.commit()
            
            return {
                "executed_tasks": executed_tasks,
                "total_tasks": total_tasks,
                "execution_time_ms": sorted_tasks.execution_time_ms,
                "algorithm_used": sorted_tasks.algorithm_used,
            }
            
        except Exception:
            try:
                build_failed = Build(
                    name=build_name,
                    tasks=build.tasks if 'build' in locals() else [],
                    status=BuildStatus.FAILED,
                    created_at=build.created_at if 'build' in locals() else datetime.utcnow(),
                )
                await build_repo.save_build(build_failed)
                await session.commit()
            except:
                pass
            raise


async def _execute_single_task(task: Task, task_repo, session) -> None:
    """
    Execute a single task (placeholder for real implementation).
    
    Args:
        task: Task to execute
        task_repo: Task repository
        session: Database session
    """
    import asyncio
    
    task_running = Task(
        name=task.name,
        dependencies=task.dependencies,
        status=TaskStatus.RUNNING,
        created_at=task.created_at,
    )
    await task_repo.save_task(task_running)
    await session.commit()
    
    await asyncio.sleep(0.5)
    
    task_completed = Task(
        name=task.name,
        dependencies=task.dependencies,
        status=TaskStatus.COMPLETED,
        created_at=task.created_at,
    )
    await task_repo.save_task(task_completed)
    await session.commit()


@celery_app.task
def validate_build_dependencies(build_name: str) -> Dict:
    """
    Validate build dependencies asynchronously.
    
    Args:
        build_name: Build name to validate
        
    Returns:
        Validation result
    """
    try:
        result = run_async(_validate_build_internal(build_name))
        return {
            "build_name": build_name,
            "is_valid": result["is_valid"],
            "issues": result["issues"],
            "validated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "build_name": build_name,
            "is_valid": False,
            "error": str(e),
            "validated_at": datetime.utcnow().isoformat(),
        }


async def _validate_build_internal(build_name: str) -> Dict:
    """Internal build validation logic."""
    from app.core.services.build_service import BuildService
    from app.core.services.topology_service import TopologyService
    from app.infrastructure.database.repositories.build_repository import SqlBuildRepository
    from app.infrastructure.database.repositories.task_repository import SqlTaskRepository
    from app.infrastructure.database.session import get_session_maker
    from app.infrastructure.cache.cache_service import CacheService
    from app.infrastructure.cache.redis_client import get_redis_client
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        build_repo = SqlBuildRepository(session)
        task_repo = SqlTaskRepository(session)
        topology_service = TopologyService()
        redis_client = get_redis_client()
        cache_service = CacheService(redis_client)
        build_service = BuildService(build_repo, task_repo, topology_service, cache_service)
        
        is_valid, issues = await build_service.validate_build_dependencies(build_name)
        return {"is_valid": is_valid, "issues": issues}


@celery_app.task
def cancel_build_execution(build_name: str) -> Dict:
    """
    Cancel running build execution.
    
    Args:
        build_name: Build name to cancel
        
    Returns:
        Cancellation result
    """
    try:
        result = run_async(_cancel_build_internal(build_name))
        return {
            "build_name": build_name,
            "cancelled": True,
            "cancelled_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "build_name": build_name,
            "cancelled": False,
            "error": str(e),
        }


async def _cancel_build_internal(build_name: str) -> Dict:
    """Internal build cancellation logic."""
    from app.core.services.build_service import BuildService
    from app.core.services.topology_service import TopologyService
    from app.infrastructure.database.repositories.build_repository import SqlBuildRepository
    from app.infrastructure.database.repositories.task_repository import SqlTaskRepository
    from app.infrastructure.database.session import get_session_maker
    from app.infrastructure.cache.cache_service import CacheService
    from app.infrastructure.cache.redis_client import get_redis_client
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        build_repo = SqlBuildRepository(session)
        task_repo = SqlTaskRepository(session)
        topology_service = TopologyService()
        redis_client = get_redis_client()
        cache_service = CacheService(redis_client)
        build_service = BuildService(build_repo, task_repo, topology_service, cache_service)
        
        cancelled_build = await build_service.cancel_build(build_name)
        await session.commit()
        
        return {"build": cancelled_build}