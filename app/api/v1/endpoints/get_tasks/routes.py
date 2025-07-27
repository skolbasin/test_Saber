"""Get tasks endpoint routes according to technical requirements."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_build_service
from app.core.services.build_service import BuildService
from app.core.exceptions import BuildNotFoundException, CircularDependencyException
from .schemas import GetTasksRequest

router = APIRouter()


@router.post(
    "/get_tasks",
    response_model=List[str],
    summary="Get sorted tasks for a build",
    description="Returns a list of task names sorted according to their dependencies. This endpoint complies with the technical requirements.",
    responses={
        200: {
            "description": "Tasks retrieved and sorted successfully",
            "content": {
                "application/json": {
                    "example": ["compile_exe", "pack_build"]
                }
            }
        },
        404: {"description": "Build not found"},
        409: {"description": "Circular dependency detected"},
        500: {"description": "Internal server error"},
    },
)
async def get_tasks(
    request: GetTasksRequest,
    build_service: BuildService = Depends(get_build_service),
) -> List[str]:
    """
    Get topologically sorted tasks for a build.
    
    This endpoint complies with the technical requirements specification:
    - Accepts POST request with JSON containing build name
    - Returns simple array of task names sorted by dependencies
    - Handles errors appropriately
    
    Args:
        request: Request containing build name
        build_service: Build service dependency
        
    Returns:
        List of task names in execution order
        
    Raises:
        HTTPException: If build not found or circular dependencies detected
    """
    try:
        # Get topological sort for the build
        result = await build_service.get_topological_sort(request.build)
        
        # Return only the sorted task names as required by the spec
        return result.tasks
        
    except BuildNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build '{request.build}' not found",
        )
    except CircularDependencyException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Circular dependency detected: {str(e)}",
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Failed to get tasks for build {request.build}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tasks for build",
        )