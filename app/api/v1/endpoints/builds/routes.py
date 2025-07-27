"""Build management API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.dependencies import get_build_service, get_current_active_user
from .schemas import (
    BuildCreateRequest,
    BuildResponse,
    BuildListResponse,
)
from app.core.auth.entities import User
from app.core.domain.entities import Build
from app.core.domain.enums import BuildStatus
from app.core.services.build_service import BuildService

router = APIRouter(prefix="/builds", tags=["Build Management"])


@router.get(
    "/",
    response_model=BuildListResponse,
    summary="List all builds",
    description="Get a paginated list of all available builds.",
    responses={
        200: {"description": "Builds retrieved successfully"},
        401: {"description": "Authentication required"},
    },
)
async def list_builds(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of builds to return"),
    offset: int = Query(0, ge=0, description="Number of builds to skip"),
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> BuildListResponse:
    """
    Get a paginated list of all available builds.
    
    Returns all builds in the system with pagination support.
    Builds include their task lists and current status.
    """
    try:
        all_builds = await build_service.get_all_builds()
        builds_list = list(all_builds.values())
        
        total_count = len(builds_list)
        paginated_builds = builds_list[offset:offset + limit]
        
        return BuildListResponse(
            builds=[BuildResponse.model_validate(build) for build in paginated_builds],
            total=total_count,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve builds",
        )


@router.post(
    "/",
    response_model=BuildResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new build",
    description="Create a new build configuration with specified tasks.",
    responses={
        201: {"description": "Build created successfully"},
        400: {"description": "Invalid build configuration"},
        409: {"description": "Build already exists"},
        401: {"description": "Authentication required"},
    },
)
async def create_build(
    build_data: BuildCreateRequest,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> BuildResponse:
    """
    Create a new build configuration.
    
    Creates a build with the specified name and task list.
    Build names must be unique across the system.
    """
    try:
        existing_build = await build_service.get_build(build_data.name)
        if existing_build:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Build '{build_data.name}' already exists",
            )
        
        build = Build(
            name=build_data.name,
            tasks=build_data.tasks,
            status=BuildStatus.PENDING,
        )
        
        created_build = await build_service.create_build(build)
        return BuildResponse.model_validate(created_build)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create build",
        )


@router.get(
    "/{build_name}",
    response_model=BuildResponse,
    summary="Get build by name",
    description="Retrieve a specific build by its name.",
    responses={
        200: {"description": "Build retrieved successfully"},
        404: {"description": "Build not found"},
        401: {"description": "Authentication required"},
    },
)
async def get_build(
    build_name: str,
    current_user: User = Depends(get_current_active_user),
    build_service: BuildService = Depends(get_build_service),
) -> BuildResponse:
    """
    Get a specific build by name.
    
    Returns detailed information about the requested build including
    its task list, status, and execution history.
    """
    try:
        build = await build_service.get_build(build_name)
        if not build:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Build '{build_name}' not found",
            )
        
        return BuildResponse.model_validate(build)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve build",
        )