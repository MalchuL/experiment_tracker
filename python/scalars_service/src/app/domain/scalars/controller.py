from enum import Enum
from datetime import datetime
from uuid import UUID
from api.cache import get_cache
from app.infrastructure.cache.cache import Cache
from fastapi import APIRouter, Depends, HTTPException, Query
from db.clickhouse import get_clickhouse_client
from .dto import (
    LastLoggedExperimentsRequestDTO,
    LastLoggedExperimentsResultDTO,
    LogScalarRequestDTO,
    LogScalarsRequestDTO,
    ScalarsPointsResultDTO,
)
from .service import ScalarsService

router = APIRouter(prefix="/scalars", tags=["scalars"])


@router.post("/log/{project_id}/{experiment_id}")
async def log_scalar(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogScalarRequestDTO,
    client=Depends(get_clickhouse_client),
    cache: Cache | None = Depends(get_cache),
):
    try:
        service = ScalarsService(client, cache)
        return await service.log_scalar(project_id, experiment_id, payload)
    except ValueError as exc:
        if str(exc) == "Scalars table does not exist":
            raise HTTPException(status_code=404, detail=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/log_batch/{project_id}/{experiment_id}")
async def log_scalars_batch(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogScalarsRequestDTO,
    client=Depends(get_clickhouse_client),
    cache: Cache | None = Depends(get_cache),
):
    service = ScalarsService(client, cache)
    return await service.log_scalars(project_id, experiment_id, payload)


class Sampling(Enum):
    RESERVOIR = "reservoir"
    UNIFORM = "uniform"
    ALL = "all"


@router.get("/get/{project_id}", response_model=ScalarsPointsResultDTO)
async def get_scalars(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    sampling: Sampling = Query(default=Sampling.RESERVOIR),
    max_points: int | None = Query(default=None, ge=1),
    client=Depends(get_clickhouse_client),
    return_tags: bool = Query(default=False),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    cache: Cache | None = Depends(get_cache),
):

    service = ScalarsService(client, cache)
    return await service.get_scalars(
        project_id,
        experiment_id,
        max_points,
        return_tags=return_tags,
        start_time=start_time,
        end_time=end_time,
    )


@router.post(
    "/last_logged/{project_id}",
    response_model=LastLoggedExperimentsResultDTO,
)
async def get_last_logged_experiments(
    project_id: UUID,
    payload: LastLoggedExperimentsRequestDTO,
    client=Depends(get_clickhouse_client),
    cache: Cache | None = Depends(get_cache),
):
    service = ScalarsService(client, cache)
    return await service.get_last_logged_experiments(
        project_id,
        experiment_ids=payload.experiment_ids,
    )
