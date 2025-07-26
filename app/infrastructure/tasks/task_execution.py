"""Celery tasks for individual task execution."""

import subprocess
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from celery import current_task

from app.core.domain.entities import Task
from app.core.domain.enums import TaskStatus
from app.infrastructure.tasks.celery_app import celery_app
from app.utils.async_helpers import run_async


@celery_app.task(bind=True, max_retries=3)
def execute_task_with_command(
    self,
    task_name: str,
    command: str,
    working_directory: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None,
    timeout: int = 3600,  # 1 hour default
) -> Dict:
    """
    Execute a task with a shell command.
    
    Args:
        task_name: Name of the task
        command: Shell command to execute
        working_directory: Working directory for command execution
        environment: Environment variables
        timeout: Command timeout in seconds
        
    Returns:
        Task execution result
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "status": f"Starting execution of task {task_name}",
            },
        )
        
        result = run_async(
            _execute_command_async(
                task_name, command, working_directory, environment, timeout, self
            )
        )
        
        return {
            "task_name": task_name,
            "status": "COMPLETED",
            "result": result,
            "completed_at": datetime.utcnow().isoformat(),
        }
        
    except subprocess.TimeoutExpired:
        return {
            "task_name": task_name,
            "status": "FAILED",
            "error": f"Task execution timed out after {timeout} seconds",
            "failed_at": datetime.utcnow().isoformat(),
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "task_name": task_name,
            "status": "FAILED",
            "error": f"Command failed with exit code {e.returncode}: {e.stderr}",
            "stdout": e.stdout,
            "stderr": e.stderr,
            "exit_code": e.returncode,
            "failed_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        
        return {
            "task_name": task_name,
            "status": "FAILED",
            "error": f"Task execution failed after {self.max_retries} retries: {str(exc)}",
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _execute_command_async(
    task_name: str,
    command: str,
    working_directory: Optional[str],
    environment: Optional[Dict[str, str]],
    timeout: int,
    task_instance,
) -> Dict:
    """
    Execute command asynchronously with progress tracking.
    
    Args:
        task_name: Task name
        command: Command to execute
        working_directory: Working directory
        environment: Environment variables
        timeout: Timeout in seconds
        task_instance: Celery task instance
        
    Returns:
        Execution result
    """
    import os
    
    await _update_task_status(task_name, TaskStatus.RUNNING)
    
    env = os.environ.copy()
    if environment:
        env.update(environment)
    
    task_instance.update_state(
        state="PROGRESS",
        meta={
            "current": 25,
            "total": 100,
            "status": f"Executing command: {command[:50]}...",
        },
    )
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_directory,
            env=env,
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
        
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""
        
        task_instance.update_state(
            state="PROGRESS",
            meta={
                "current": 90,
                "total": 100,
                "status": f"Command completed with exit code {process.returncode}",
            },
        )
        
        if process.returncode == 0:
            await _update_task_status(task_name, TaskStatus.COMPLETED)
        else:
            await _update_task_status(task_name, TaskStatus.FAILED, stderr_text)
            raise subprocess.CalledProcessError(
                process.returncode, command, stdout_text, stderr_text
            )
        
        return {
            "exit_code": process.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "command": command,
        }
        
    except asyncio.TimeoutError:
        if process:
            process.kill()
            await process.wait()
        
        await _update_task_status(task_name, TaskStatus.FAILED, f"Timeout after {timeout}s")
        raise subprocess.TimeoutExpired(command, timeout)


async def _update_task_status(
    task_name: str, status: TaskStatus, error_message: Optional[str] = None
) -> None:
    """Update task status in database."""
    from app.infrastructure.database.repositories.task_repository import SqlTaskRepository
    from app.infrastructure.database.session import get_session_maker
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            task_repo = SqlTaskRepository(session)
            task = await task_repo.get_task(task_name)
            
            if task:
                updated_task = Task(
                    name=task.name,
                    dependencies=task.dependencies,
                    status=status,
                    created_at=task.created_at,
                    error_message=error_message,
                )
                await task_repo.save_task(updated_task)
                await session.commit()
                
        except Exception:
            pass


@celery_app.task
def execute_parallel_tasks(
    task_commands: List[Dict[str, Any]], max_workers: int = 4
) -> Dict:
    """
    Execute multiple tasks in parallel.
    
    Args:
        task_commands: List of task command configurations
        max_workers: Maximum number of parallel workers
        
    Returns:
        Parallel execution results
    """
    try:
        result = run_async(_execute_parallel_internal(task_commands, max_workers))
        return {
            "status": "COMPLETED",
            "results": result,
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _execute_parallel_internal(
    task_commands: List[Dict[str, Any]], max_workers: int
) -> List[Dict]:
    """Execute tasks in parallel with semaphore."""
    semaphore = asyncio.Semaphore(max_workers)
    
    async def execute_single(task_config: Dict[str, Any]) -> Dict:
        async with semaphore:
            try:
                result = await _execute_command_async(
                    task_config["task_name"],
                    task_config["command"],
                    task_config.get("working_directory"),
                    task_config.get("environment"),
                    task_config.get("timeout", 3600),
                    current_task,
                )
                return {
                    "task_name": task_config["task_name"],
                    "status": "COMPLETED",
                    "result": result,
                }
            except Exception as e:
                return {
                    "task_name": task_config["task_name"],
                    "status": "FAILED",
                    "error": str(e),
                }
    
    results = await asyncio.gather(
        *[execute_single(config) for config in task_commands],
        return_exceptions=True,
    )
    
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "task_name": task_commands[i]["task_name"],
                "status": "FAILED",
                "error": str(result),
            })
        else:
            processed_results.append(result)
    
    return processed_results


@celery_app.task
def execute_docker_task(
    task_name: str,
    image: str,
    command: Optional[str] = None,
    volumes: Optional[Dict[str, str]] = None,
    environment: Optional[Dict[str, str]] = None,
    working_dir: Optional[str] = None,
    timeout: int = 3600,
) -> Dict:
    """
    Execute a task in Docker container.
    
    Args:
        task_name: Name of the task
        image: Docker image to use
        command: Command to run in container
        volumes: Volume mounts (host_path: container_path)
        environment: Environment variables
        working_dir: Working directory in container
        timeout: Execution timeout
        
    Returns:
        Docker task execution result
    """
    try:
        result = run_async(
            _execute_docker_internal(
                task_name, image, command, volumes, environment, working_dir, timeout
            )
        )
        return {
            "task_name": task_name,
            "status": "COMPLETED",
            "result": result,
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "task_name": task_name,
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


async def _execute_docker_internal(
    task_name: str,
    image: str,
    command: Optional[str],
    volumes: Optional[Dict[str, str]],
    environment: Optional[Dict[str, str]],
    working_dir: Optional[str],
    timeout: int,
) -> Dict:
    """Execute Docker task internally."""
    import shlex
    
    docker_cmd = ["docker", "run", "--rm"]
    
    if volumes:
        for host_path, container_path in volumes.items():
            docker_cmd.extend(["-v", f"{host_path}:{container_path}"])
    
    if environment:
        for key, value in environment.items():
            docker_cmd.extend(["-e", f"{key}={value}"])
    
    if working_dir:
        docker_cmd.extend(["-w", working_dir])
    
    docker_cmd.append(image)
    
    if command:
        docker_cmd.extend(shlex.split(command))
    
    full_command = " ".join(shlex.quote(arg) for arg in docker_cmd)
    
    return await _execute_command_async(
        task_name, full_command, None, None, timeout, current_task
    )