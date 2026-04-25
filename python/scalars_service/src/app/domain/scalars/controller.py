from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.service_dependencies import get_scalars_service
from .dto import (
    LogScalarRequestDTO,
    LogScalarsRequestDTO,
    ScalarsPointsResultDTO,
    ScalarsSampling,
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
    return await service.log_scalar(project_id, experiment_id, payload)


@router.post("/log_batch/{project_id}/{experiment_id}")
async def log_scalars_batch(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogScalarsRequestDTO,
    service: ScalarsService = Depends(get_scalars_service),
):
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
    service: ScalarsService = Depends(get_scalars_service),
):
    return await service.get_scalars(
        project_id,
        experiment_id,
        limit=limit,
        offset=offset,
        max_points=max_points,
        return_tags=return_tags,
        start_time=start_time,
        end_time=end_time,
        sampling=sampling,
        columns_per_query=columns_per_query,
    )


