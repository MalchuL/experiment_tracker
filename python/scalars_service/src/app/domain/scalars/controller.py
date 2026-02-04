from enum import Enum
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
):

    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        microseconds=1000
    )
    await conn.execute(
        SCALARS_DB_UTILS.build_insert_statement(table_name),
        timestamp,
        experiment_id,
        request.scalar_name,
        request.value,
        request.step,
        json.dumps(request.tags),
    )
    return {"status": "logged"}


class Sampling(Enum):
    RESERVOIR = "reservoir"
    UNIFORM = "uniform"
    ALL = "all"


@router.get("/get/{project_id}/{experiment_id}")
async def get_scalars(
    project_id: str,
    experiment_id: str,
    sampling: Sampling = Query(default=Sampling.RESERVOIR),
    max_points: int | None = Query(default=None, ge=1),
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
):

    service = ScalarsService(conn)
    result = await service.get_scalars(
        project_id, experiment_id, max_points, return_tags=True
    )
    return result
