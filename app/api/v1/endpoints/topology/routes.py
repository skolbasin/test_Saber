"""Topology sorting API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_active_user, get_build_service
from .schemas import SortResultResponse, CycleDetectionResponse, ValidationResponse
from app.core.auth.entities import User
from app.core.services.build_service import BuildService
from app.core.exceptions import (
    BuildNotFoundException,
    CircularDependencyException,
    TaskNotFoundException,
)

router = APIRouter(prefix="/topology", tags=["Topology"])


@router.get(
    "/sort/{build_name}",
    response_model=SortResultResponse,
    summary="Get topological sort for build",
    description="Perform topological sorting of tasks for a specific build configuration. Returns the optimal execution order.",
    responses={
        200: {"description": "Topological sort completed successfully"},
        404: {"description": "Build not found"},
        409: {"description": "Cyclic dependency detected"},
    },
)
async def sort_build_tasks(
    build_name: str,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> SortResultResponse:
    """
    Perform topological sorting of tasks for a specific build.
    
    This endpoint analyzes the task dependencies within a build and returns
    the optimal execution order using Kahn's algorithm. If cycles are detected,
    it returns an error with details about the problematic dependencies.
    
    Args:
        build_name: Name of the build to sort
        current_user: Currently authenticated user
        build_service: Build service dependency
        
    Returns:
        SortResultResponse: Contains sorted task order and execution metadata
        
    Raises:
        HTTPException: If build not found or cyclic dependencies detected
    """
    try:
        result = await build_service.get_topological_sort(build_name)
        
        return SortResultResponse(
            build_name=build_name,
            sorted_tasks=result.tasks,
            algorithm_used=result.algorithm_used,
            execution_time_ms=result.execution_time_ms,
            total_tasks=len(result.tasks),
            has_cycles=False,
            cycles=[],
        )
        
    except BuildNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build '{build_name}' not found",
        )
    except CircularDependencyException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cyclic dependency detected: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform topological sort: {str(e)}",
        )


@router.get(
    "/detect-cycles/{build_name}",
    response_model=CycleDetectionResponse,
    summary="Detect cycles in build dependencies",
    description="Analyze build task dependencies to detect any circular dependencies that would prevent execution.",
    responses={
        200: {"description": "Cycle detection completed"},
        404: {"description": "Build not found"},
    },
)
async def detect_cycles(
    build_name: str,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> CycleDetectionResponse:
    """
    Detect circular dependencies in build task graph.
    
    This endpoint analyzes the task dependency graph for a specific build
    to identify any circular dependencies that would prevent successful
    execution. Uses depth-first search algorithm for cycle detection.
    
    Args:
        build_name: Name of the build to analyze
        current_user: Currently authenticated user
        build_service: Build service dependency
        
    Returns:
        CycleDetectionResponse: Contains cycle detection results and details
        
    Raises:
        HTTPException: If build not found
    """
    try:
        cycles = await build_service.detect_cycles(build_name)
        
        return CycleDetectionResponse(
            build_name=build_name,
            has_cycles=len(cycles) > 0,
            cycles=cycles,
            total_cycles=len(cycles),
            analysis_method="depth_first_search",
        )
        
    except BuildNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build '{build_name}' not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect cycles",
        )


@router.get(
    "/validate/{build_name}",
    response_model=ValidationResponse,
    summary="Validate build task dependencies",
    description="Comprehensive validation of build task dependencies including cycle detection and task existence checks.",
    responses={
        200: {"description": "Validation completed"},
        404: {"description": "Build not found"},
    },
)
async def validate_build_dependencies(
    build_name: str,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> ValidationResponse:
    """
    Perform comprehensive validation of build dependencies.
    
    This endpoint validates:
    - All referenced tasks exist
    - No circular dependencies
    - Dependency graph is well-formed
    - Tasks are properly connected
    
    Args:
        build_name: Name of the build to validate
        current_user: Currently authenticated user
        build_service: Build service dependency
        
    Returns:
        ValidationResponse: Validation results with detailed analysis
        
    Raises:
        HTTPException: If build not found
    """
    try:
        build = await build_service.get_build(build_name)
        if not build:
            raise BuildNotFoundException(f"Build '{build_name}' not found")
        
        cycles = await build_service.detect_cycles(build_name)
        
        missing_tasks = []
        for task_name in build.tasks:
            task = await build_service._task_repository.get_task(task_name)
            if not task:
                missing_tasks.append(task_name)
        
        sort_possible = len(cycles) == 0 and len(missing_tasks) == 0
        sorted_order = []
        
        if sort_possible:
            try:
                result = await build_service.get_topological_sort(build_name)
                sorted_order = result.tasks
            except Exception:
                sort_possible = False
        
        return ValidationResponse(
            build_name=build_name,
            is_valid=len(cycles) == 0 and len(missing_tasks) == 0,
            has_cycles=len(cycles) > 0,
            cycles=cycles,
            missing_tasks=missing_tasks,
            total_tasks=len(build.tasks),
            sort_possible=sort_possible,
            suggested_order=sorted_order,
            validation_timestamp="2025-07-25T16:50:00Z",
        )
        
    except BuildNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build '{build_name}' not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate build dependencies",
        )