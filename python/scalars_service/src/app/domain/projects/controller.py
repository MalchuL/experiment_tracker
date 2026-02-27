from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api.service_dependencies import get_projects_service
from .dto import CreateProjectTableDTO
from .service import ProjectsService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("")
async def create_project_scalars_table(
    payload: CreateProjectTableDTO,
    service: ProjectsService = Depends(get_projects_service),
):
    try:
        result = await service.create_project_table(payload.project_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating table: {str(e)}")


@router.get("/exists/{project_id}")
async def get_project_table_existence(
    project_id: UUID,
    service: ProjectsService = Depends(get_projects_service),
):
    try:
        return await service.get_project_table_existence(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking table existence: {str(e)}"
        )


@router.get("/experiments/{project_id}")
async def get_project_experiments_ids(
    project_id: UUID,
    service: ProjectsService = Depends(get_projects_service),
):
    try:
        return await service.get_project_experiments_ids(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting experiments IDs: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project_table(
    project_id: UUID,
    service: ProjectsService = Depends(get_projects_service),
):
    try:
        return await service.delete_project_table(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting table: {str(e)}")
