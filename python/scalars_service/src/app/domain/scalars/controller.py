"""FastAPI routes for scalar time series reads and writes (per-project ClickHouse wide table).

Compaction drops empty mapped metric columns on the scalars table. Cross-table cleanup,
usage, and admin storage routes live under ``/projects`` in ``projects.controller``.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.service_dependencies import get_scalars_service
from .dto import (
    LogScalarRequestDTO,
    LogScalarsRequestDTO,
    ScalarsPointsResultDTO,
    ScalarsSampling,
    CompactProjectColumnsResponseDTO,
    ScalarNamesResponseDTO,
)
from .service import ScalarsService

router = APIRouter(prefix="/scalars", tags=["scalars"])


@router.post("/log/{project_id}/{experiment_id}")
async def log_scalar(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogScalarRequestDTO,
    service: ScalarsService = Depends(get_scalars_service),
):
    """Append one step row with one or more metric values for an experiment."""
    return await service.log_scalar(project_id, experiment_id, payload)


@router.post("/log_batch/{project_id}/{experiment_id}")
async def log_scalars_batch(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogScalarsRequestDTO,
    service: ScalarsService = Depends(get_scalars_service),
):
    """Append multiple step rows in a single request for an experiment."""
    return await service.log_scalars(project_id, experiment_id, payload)


@router.get("/get/{project_id}", response_model=ScalarsPointsResultDTO)
async def get_scalars(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
    sampling: ScalarsSampling = Query(default=ScalarsSampling.UNIFORM),
    max_points: int | None = Query(default=None, ge=1),
    columns_per_query: int = Query(default=1, ge=1, le=32),
    return_tags: bool = Query(default=False),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    start_step: int | None = Query(default=None),
    end_step: int | None = Query(default=None),
    scalar_name: list[str] | None = Query(default=None),
    store_cache: bool = Query(default=True),
    service: ScalarsService = Depends(get_scalars_service),
):
    """Read scalar series for a project, optionally filtered to experiments and time range.

    Paginates by experiment first, then loads each metric column with optional
    ``max_points`` uniform sampling across non-null rows per experiment.
    """
    return await service.get_scalars(
        project_id,
        experiment_id,
        limit=limit,
        offset=offset,
        max_points=max_points,
        return_tags=return_tags,
        start_time=start_time,
        end_time=end_time,
        start_step=start_step,
        end_step=end_step,
        scalar_names=scalar_name,
        store_cache=store_cache,
        sampling=sampling,
        columns_per_query=columns_per_query,
    )


@router.get("/names/{project_id}", response_model=ScalarNamesResponseDTO)
async def get_scalar_names(
    project_id: UUID,
    service: ScalarsService = Depends(get_scalars_service),
):
    """Return scalar names known for a project without loading scalar point values."""
    return await service.get_scalar_names(project_id)


@router.post(
    "/projects/{project_id}/compact-columns",
    response_model=CompactProjectColumnsResponseDTO,
)
async def compact_project_columns(
    project_id: UUID,
    service: ScalarsService = Depends(get_scalars_service),
):
    """Drop all-null metric columns from ClickHouse and remove them from the scalar mapping.

    Base columns (timestamp, experiment id, step, tags) are not affected.
    """
    return await service.compact_project_columns(project_id)
