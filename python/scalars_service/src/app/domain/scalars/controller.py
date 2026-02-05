from enum import Enum
from api.cache import get_cache
from app.infrastructure.cache.cache import Cache
from fastapi import APIRouter, Depends, Query
from db.clickhouse import get_clickhouse_client
from .dto import (
    LogScalarRequestDTO,
    LogScalarsRequestDTO,
)
from .service import ScalarsService

router = APIRouter(prefix="/scalars", tags=["scalars"])

@router.post("/log/{project_id}/{experiment_id}")
async def log_scalar(
    project_id: str,
    experiment_id: str,
    request: LogScalarRequestDTO,
    client = Depends(get_clickhouse_client),
    cache: Cache | None = Depends(get_cache),
):
    service = ScalarsService(client, cache)
    return await service.log_scalar(project_id, experiment_id, request)


@router.post("/log_batch/{project_id}/{experiment_id}")
async def log_scalars_batch(
    project_id: str,
    experiment_id: str,
    request: LogScalarsRequestDTO,
    client = Depends(get_clickhouse_client),
    cache: Cache | None = Depends(get_cache),
):
    service = ScalarsService(client, cache)
    return await service.log_scalars(project_id, experiment_id, request)


class Sampling(Enum):
    RESERVOIR = "reservoir"
    UNIFORM = "uniform"
    ALL = "all"


@router.get("/get/{project_id}")
async def get_scalars(
    project_id: str,
    experiment_id: list[str] | None = Query(default=None),
    sampling: Sampling = Query(default=Sampling.RESERVOIR),
    max_points: int | None = Query(default=None, ge=1),
    client = Depends(get_clickhouse_client),
    return_tags: bool = Query(default=False),
    cache: Cache | None = Depends(get_cache),
):

    service = ScalarsService(client, cache)
    result = await service.get_scalars(
        project_id, experiment_id, max_points, return_tags=return_tags
    )
    return result
