from fastapi import APIRouter, HTTPException, Depends, Request
from db.clickhouse import get_clickhouse_client  # type: ignore

from .dto import CreateProjectTableDTO
from .service import ProjectsService
from app.domain.utils.msgpack_utils import (  # type: ignore
    parse_request_model,
    pack_response,
)


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("")
async def create_project_scalars_table(
    request: Request,
    client=Depends(get_clickhouse_client),
):
    try:
        payload = await parse_request_model(request, CreateProjectTableDTO)
        service = ProjectsService(client)
        result = await service.create_project_table(payload.project_id)
        return pack_response(request, result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating table: {str(e)}")


@router.get("/exists/{project_id}")
async def get_project_table_existence(
    project_id: str,
    client=Depends(get_clickhouse_client),
):
    try:
        service = ProjectsService(client)
        return await service.get_project_table_existence(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking table existence: {str(e)}"
        )


@router.get("/experiments/{project_id}")
async def get_project_experiments_ids(
    project_id: str,
    client=Depends(get_clickhouse_client),
):
    try:
        service = ProjectsService(client)
        return await service.get_project_experiments_ids(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting experiments IDs: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project_table(
    project_id: str,
    client=Depends(get_clickhouse_client),
):
    try:
        service = ProjectsService(client)
        return await service.delete_project_table(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting table: {str(e)}")
