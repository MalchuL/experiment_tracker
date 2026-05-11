"""FastAPI routes for ClickHouse project tables and cross-domain project operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.service_dependencies import get_projects_service
from .dto import (
    CreateProjectTableDTO,
    DeleteExperimentScalarsDataResponseDTO,
    DropManagedStorageTableResponseDTO,
    ExperimentClickhouseUsageResponseDTO,
    ListStorageTablesResponseDTO,
    ProjectClickhouseUsageResponseDTO,
)
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


@router.delete(
    "/{project_id}/experiments/{experiment_id}",
    response_model=DeleteExperimentScalarsDataResponseDTO,
)
async def delete_experiment_clickhouse_data(
    project_id: UUID,
    experiment_id: UUID,
    service: ProjectsService = Depends(get_projects_service),
):
    """Delete rows for one experiment from scalars, artifacts_info, and last_logged tables."""
    return await service.delete_experiment_data(project_id, experiment_id)


@router.get(
    "/{project_id}/usage",
    response_model=ProjectClickhouseUsageResponseDTO,
)
async def get_project_clickhouse_usage(
    project_id: UUID,
    service: ProjectsService = Depends(get_projects_service),
):
    """Row counts, column counts, and on-disk bytes per project ClickHouse table."""
    return await service.get_project_usage(project_id)


@router.get(
    "/{project_id}/experiments/{experiment_id}/usage",
    response_model=ExperimentClickhouseUsageResponseDTO,
)
async def get_experiment_clickhouse_usage(
    project_id: UUID,
    experiment_id: UUID,
    service: ProjectsService = Depends(get_projects_service),
):
    """Estimated scalars-table bytes for one experiment from row share."""
    return await service.get_experiment_usage(project_id, experiment_id)


@router.get(
    "/admin/storage/tables",
    response_model=ListStorageTablesResponseDTO,
)
async def list_clickhouse_storage_tables(
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ProjectsService = Depends(get_projects_service),
):
    """List ``scalars_*`` and ``artifacts_info_*`` tables (admin, filter, paginate)."""
    return await service.list_storage_tables(q=q, limit=limit, offset=offset)


@router.delete(
    "/admin/storage/tables/{table_name}",
    response_model=DropManagedStorageTableResponseDTO,
)
async def drop_clickhouse_storage_table(
    table_name: str,
    service: ProjectsService = Depends(get_projects_service),
):
    """Drop a managed scalars-service table (admin, restricted prefixes)."""
    return await service.drop_table(table_name)


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
