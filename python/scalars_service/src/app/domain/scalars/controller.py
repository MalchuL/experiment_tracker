from enum import Enum
from api.cache import get_cache
from app.infrastructure.cache.cache import Cache
from fastapi import APIRouter, Depends, Query
from db.questdb import get_asyncpg_connection
from sqlalchemy import Table, MetaData
from datetime import datetime, timedelta, timezone
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS
import json
from .dto import (
    LogScalarRequestDTO,
)
import asyncpg
from .service import ScalarsService

router = APIRouter(prefix="/scalars", tags=["scalars"])

metadata = MetaData()


@router.post("/log/{project_id}/{experiment_id}")
async def log_scalar(
    project_id: str,
    experiment_id: str,
    request: LogScalarRequestDTO,
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
    cache: Cache | None = Depends(get_cache),
):
    service = ScalarsService(conn, cache)
    await service.log_scalar(project_id, experiment_id, request)
    return {"status": "logged"}


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
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
    return_tags: bool = Query(default=False),
    cache: Cache | None = Depends(get_cache),
):

    service = ScalarsService(conn, cache)
    result = await service.get_scalars(
        project_id, experiment_id, max_points, return_tags=return_tags
    )
    return result
