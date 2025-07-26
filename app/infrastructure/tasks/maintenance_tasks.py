"""Celery tasks for system maintenance and cleanup."""

from datetime import datetime, timedelta
from typing import Dict

from app.infrastructure.tasks.celery_app import celery_app
from app.utils.async_helpers import run_async


@celery_app.task
def cleanup_expired_tokens() -> Dict:
    """
    Clean up expired refresh tokens from database.
    
    Returns:
        Cleanup result with count of removed tokens
    """
    try:
        result = run_async(_cleanup_tokens_internal())
        return {
            "status": "COMPLETED",
            "tokens_removed": result["tokens_removed"],
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _cleanup_tokens_internal() -> Dict:
    """Internal token cleanup logic."""
    from app.infrastructure.database.repositories.refresh_token_repository import SqlRefreshTokenRepository
    from app.infrastructure.database.session import get_session_maker
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        refresh_token_repo = SqlRefreshTokenRepository(session)
        tokens_removed = await refresh_token_repo.cleanup_expired_tokens()
        await session.commit()
        
        return {"tokens_removed": tokens_removed}


@celery_app.task
def cleanup_old_build_results() -> Dict:
    """
    Clean up old build results and logs.
    
    Returns:
        Cleanup result
    """
    try:
        result = run_async(_cleanup_builds_internal())
        return {
            "status": "COMPLETED",
            "builds_cleaned": result["builds_cleaned"],
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _cleanup_builds_internal() -> Dict:
    """Internal build cleanup logic."""
    from app.core.domain.enums import BuildStatus
    from app.infrastructure.database.repositories.build_repository import SqlBuildRepository
    from app.infrastructure.database.session import get_session_maker
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        build_repo = SqlBuildRepository(session)
        
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        all_builds = await build_repo.get_all_builds()
        
        builds_to_clean = []
        for build_name, build in all_builds.items():
            if (build.created_at and 
                build.created_at < cutoff_date and 
                build.status in [BuildStatus.COMPLETED, BuildStatus.FAILED]):
                builds_to_clean.append(build_name)
        
        builds_cleaned = len(builds_to_clean)
        
        return {"builds_cleaned": builds_cleaned}


@celery_app.task
def health_check_services() -> Dict:
    """
    Perform health checks on external services.
    
    Returns:
        Health check results
    """
    try:
        result = run_async(_health_check_internal())
        return {
            "status": "COMPLETED",
            "services": result["services"],
            "overall_health": result["overall_health"],
            "checked_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _health_check_internal() -> Dict:
    """Internal health check logic."""
    from app.infrastructure.cache.redis_client import get_redis_client
    from app.infrastructure.database.session import get_session_maker
    
    services = {}
    
    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            await session.execute("SELECT 1")
            services["database"] = "healthy"
    except Exception as e:
        services["database"] = f"unhealthy: {str(e)}"
    
    try:
        redis_client = get_redis_client()
        is_healthy = await redis_client.ping()
        services["redis"] = "healthy" if is_healthy else "unhealthy"
    except Exception as e:
        services["redis"] = f"unhealthy: {str(e)}"
    
    try:
        from app.infrastructure.tasks.celery_app import celery_app
        broker_info = celery_app.control.inspect().stats()
        services["celery_broker"] = "healthy" if broker_info else "unhealthy"
    except Exception as e:
        services["celery_broker"] = f"unhealthy: {str(e)}"
    
    unhealthy_services = [
        name for name, status in services.items() 
        if not status.startswith("healthy")
    ]
    overall_health = "healthy" if not unhealthy_services else "degraded"
    
    return {
        "services": services,
        "overall_health": overall_health,
        "unhealthy_services": unhealthy_services,
    }


@celery_app.task
def cleanup_cache_data() -> Dict:
    """
    Clean up old cache data and optimize Redis memory usage.
    
    Returns:
        Cache cleanup result
    """
    try:
        result = run_async(_cleanup_cache_internal())
        return {
            "status": "COMPLETED",
            "cache_entries_removed": result["cache_entries_removed"],
            "memory_freed": result.get("memory_freed", "unknown"),
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _cleanup_cache_internal() -> Dict:
    """Internal cache cleanup logic."""
    from app.infrastructure.cache.redis_client import get_redis_client
    
    redis_client = get_redis_client()
    
    info_before = await redis_client.get_info()
    memory_before = info_before.get("used_memory", 0)
    
    old_sorted_keys = await redis_client.clear_pattern("sorted:*")
    
    old_status_keys = await redis_client.clear_pattern("status:*")
    
    info_after = await redis_client.get_info()
    memory_after = info_after.get("used_memory", 0)
    
    return {
        "cache_entries_removed": old_sorted_keys + old_status_keys,
        "memory_freed": memory_before - memory_after,
    }


@celery_app.task
def generate_system_report() -> Dict:
    """
    Generate comprehensive system health and usage report.
    
    Returns:
        System report data
    """
    try:
        result = run_async(_generate_report_internal())
        return {
            "status": "COMPLETED",
            "report": result,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _generate_report_internal() -> Dict:
    """Generate internal system report."""
    from app.infrastructure.database.repositories.build_repository import SqlBuildRepository
    from app.infrastructure.database.repositories.task_repository import SqlTaskRepository
    from app.infrastructure.database.repositories.user_repository import SqlUserRepository
    from app.infrastructure.database.session import get_session_maker
    from app.infrastructure.cache.redis_client import get_redis_client
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        build_repo = SqlBuildRepository(session)
        task_repo = SqlTaskRepository(session)
        redis_client = get_redis_client()
        
        all_builds = await build_repo.get_all_builds()
        all_tasks = await task_repo.get_all_tasks()
        
        build_stats = {
            "total_builds": len(all_builds),
            "builds_by_status": {},
        }
        
        for build in all_builds.values():
            status = build.status.value
            build_stats["builds_by_status"][status] = build_stats["builds_by_status"].get(status, 0) + 1
        
        task_stats = {
            "total_tasks": len(all_tasks),
            "tasks_by_status": {},
            "average_dependencies": 0,
        }
        
        total_deps = 0
        for task in all_tasks.values():
            status = task.status.value
            task_stats["tasks_by_status"][status] = task_stats["tasks_by_status"].get(status, 0) + 1
            total_deps += len(task.dependencies)
        
        if all_tasks:
            task_stats["average_dependencies"] = total_deps / len(all_tasks)
        
        redis_info = await redis_client.get_info()
        cache_stats = {
            "memory_usage": redis_info.get("used_memory_human", "unknown"),
            "connected_clients": redis_info.get("connected_clients", 0),
            "total_commands_processed": redis_info.get("total_commands_processed", 0),
            "keyspace": redis_info.get("db0", {}),
        }
        
        health_result = await _health_check_internal()
        
        return {
            "build_statistics": build_stats,
            "task_statistics": task_stats,
            "cache_statistics": cache_stats,
            "system_health": health_result,
            "report_timestamp": datetime.utcnow().isoformat(),
        }


@celery_app.task
def backup_configuration() -> Dict:
    """
    Backup system configuration and critical data.
    
    Returns:
        Backup operation result
    """
    try:
        result = run_async(_backup_config_internal())
        return {
            "status": "COMPLETED",
            "backup_location": result["backup_location"],
            "items_backed_up": result["items_backed_up"],
            "backup_size": result.get("backup_size", "unknown"),
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _backup_config_internal() -> Dict:
    """Internal configuration backup logic."""
    import json
    from pathlib import Path
    
    from app.infrastructure.database.repositories.build_repository import SqlBuildRepository
    from app.infrastructure.database.repositories.task_repository import SqlTaskRepository
    from app.infrastructure.database.session import get_session_maker
    
    backup_dir = Path("backups") / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        build_repo = SqlBuildRepository(session)
        task_repo = SqlTaskRepository(session)
        
        all_builds = await build_repo.get_all_builds()
        builds_data = {
            name: {
                "name": build.name,
                "tasks": build.tasks,
                "status": build.status.value,
                "created_at": build.created_at.isoformat() if build.created_at else None,
                "updated_at": build.updated_at.isoformat() if build.updated_at else None,
                "error_message": build.error_message,
            }
            for name, build in all_builds.items()
        }
        
        builds_file = backup_dir / "builds.json"
        with open(builds_file, "w") as f:
            json.dump(builds_data, f, indent=2)
        
        all_tasks = await task_repo.get_all_tasks()
        tasks_data = {
            name: {
                "name": task.name,
                "dependencies": list(task.dependencies),
                "status": task.status.value,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "error_message": task.error_message,
            }
            for name, task in all_tasks.items()
        }
        
        tasks_file = backup_dir / "tasks.json"
        with open(tasks_file, "w") as f:
            json.dump(tasks_data, f, indent=2)
        
        backup_size = sum(
            f.stat().st_size for f in backup_dir.rglob("*") if f.is_file()
        )
        
        return {
            "backup_location": str(backup_dir),
            "items_backed_up": ["builds", "tasks"],
            "backup_size": f"{backup_size} bytes",
        }