"""Task management API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.dependencies import get_build_service, get_current_active_user
from .schemas import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TaskListResponse,
)
from app.core.auth.entities import User
from app.core.domain.entities import Task
from app.core.domain.enums import TaskStatus
from app.core.services.build_service import BuildService

router = APIRouter(prefix="/tasks", tags=["Task Management"])


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="List all tasks",
    description="Get a paginated list of all available tasks.",
    responses={
        200: {"description": "Tasks retrieved successfully"},
        401: {"description": "Authentication required"},
    },
)
async def list_tasks(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> TaskListResponse:
    """
    Get a paginated list of all available tasks.
    
    Returns all tasks in the system with pagination support.
    Tasks include their dependencies and current status.
    """
    try:
        all_tasks = await build_service._task_repository.get_all_tasks()
        tasks_list = list(all_tasks.values())
        
        total_count = len(tasks_list)
        paginated_tasks = tasks_list[offset:offset + limit]
        
        return TaskListResponse(
            tasks=[TaskResponse.model_validate(task) for task in paginated_tasks],
            total=total_count,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks",
        )


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new task",
    description="Create a new task with specified dependencies.",
    responses={
        201: {"description": "Task created successfully"},
        400: {"description": "Invalid task configuration"},
        409: {"description": "Task already exists"},
        401: {"description": "Authentication required"},
    },
)
async def create_task(
    task_data: TaskCreateRequest,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> TaskResponse:
    """
    Create a new task.
    
    Creates a task with the specified name and dependencies.
    Task names must be unique across the system.
    """
    try:
        existing_task = await build_service._task_repository.get_task(task_data.name)
        if existing_task:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task '{task_data.name}' already exists",
            )
        
        task = Task(
            name=task_data.name,
            dependencies=set(task_data.dependencies),
            status=TaskStatus.PENDING,
        )
        
        created_task = await build_service._task_repository.save_task(task)
        return TaskResponse.model_validate(created_task)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task",
        )


@router.get(
    "/{task_name}",
    response_model=TaskResponse,
    summary="Get task by name",
    description="Retrieve a specific task by its name.",
    responses={
        200: {"description": "Task retrieved successfully"},
        404: {"description": "Task not found"},
        401: {"description": "Authentication required"},
    },
)
async def get_task(
    task_name: str,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> TaskResponse:
    """
    Get a specific task by name.
    
    Returns detailed information about the requested task including
    its dependencies, status, and execution history.
    """
    try:
        task = await build_service._task_repository.get_task(task_name)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_name}' not found",
            )
        
        return TaskResponse.model_validate(task)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task",
        )


@router.put(
    "/{task_name}",
    response_model=TaskResponse,
    summary="Update task",
    description="Update an existing task's configuration.",
    responses={
        200: {"description": "Task updated successfully"},
        404: {"description": "Task not found"},
        400: {"description": "Invalid task configuration"},
        401: {"description": "Authentication required"},
    },
)
async def update_task(
    task_name: str,
    task_update: TaskUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> TaskResponse:
    """
    Update an existing task.
    
    Allows updating task dependencies and status.
    Task name cannot be changed.
    """
    try:
        existing_task = await build_service._task_repository.get_task(task_name)
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_name}' not found",
            )
        
        updated_task = Task(
            name=existing_task.name,
            dependencies=set(task_update.dependencies) if task_update.dependencies is not None else existing_task.dependencies,
            status=task_update.status if task_update.status is not None else existing_task.status,
            created_at=existing_task.created_at,
            error_message=existing_task.error_message,
        )
        
        saved_task = await build_service._task_repository.save_task(updated_task)
        return TaskResponse.model_validate(saved_task)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task",
        )


@router.delete(
    "/{task_name}",
    summary="Delete task",
    description="Delete a task from the system.",
    responses={
        200: {"description": "Task deleted successfully"},
        404: {"description": "Task not found"},
        400: {"description": "Task cannot be deleted (used by builds)"},
        401: {"description": "Authentication required"},
    },
)
async def delete_task(
    task_name: str,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> dict:
    """
    Delete a task from the system.
    
    Task can only be deleted if it's not referenced by any builds.
    """
    try:
        task = await build_service._task_repository.get_task(task_name)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_name}' not found",
            )

        deleted = await build_service._task_repository.delete_task(task_name)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete task",
            )
        
        return {"message": f"Task '{task_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task",
        )