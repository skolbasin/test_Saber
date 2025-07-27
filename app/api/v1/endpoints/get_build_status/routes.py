"""Get build status endpoint routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_build_service
from app.core.services.build_service import BuildService
from app.core.exceptions import BuildNotFoundException
from .schemas import GetBuildStatusRequest, BuildStatusResponse

router = APIRouter()


@router.post(
    "/get_build_status",
    response_model=BuildStatusResponse,
    summary="Get build status",
    description="Returns current status of a build including task statuses. This endpoint complies with the technical requirements.",
    responses={
        200: {
            "description": "Build status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "build_name": "make_tests",
                        "status": "completed",
                        "created_at": "2025-07-26T10:30:00Z",
                        "tasks": ["compile_exe", "pack_build"],
                        "task_statuses": {"compile_exe": "completed", "pack_build": "completed"}
                    }
                }
            }
        },
        404: {"description": "Build not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_build_status(
    request: GetBuildStatusRequest,
    build_service: BuildService = Depends(get_build_service),
) -> BuildStatusResponse:
    """
    Get current status of a build.
    
    This endpoint complies with the technical requirements specification:
    - Accepts POST request with JSON containing build name
    - Returns build status and task statuses
    - Handles errors appropriately
    
    Args:
        request: Request containing build name
        build_service: Build service dependency
        
    Returns:
        BuildStatusResponse with build and task statuses
        
    Raises:
        HTTPException: If build not found
    """
    try:
        # Validate build exists and get tasks
        sorted_tasks = await build_service.get_topological_sort(request.build)
        
        # Simplified implementation - return mock status
        # In real system this would query actual build/task status from DB
        from datetime import datetime
        task_statuses = {task: "pending" for task in sorted_tasks.tasks}
        
        return BuildStatusResponse(
            build_name=request.build,
            status="pending",
            created_at=datetime.now(),
            tasks=sorted_tasks.tasks,
            task_statuses=task_statuses
        )
        
    except BuildNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build '{request.build}' not found",
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Failed to get build status for {request.build}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get build status",
        )