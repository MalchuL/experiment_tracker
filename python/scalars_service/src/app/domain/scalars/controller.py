from app.domain.projects.controller import safe_scalars_table_name
from app.domain.scalars.models import scalars_model
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
import io
from db.questdb import engine, get_async_session, get_asyncpg_connection
from sqlalchemy import Table, MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession
import json
from .dto import (
    LogScalarRequestDTO,
)
import asyncpg

router = APIRouter(prefix="/scalars", tags=["scalars"])

metadata = MetaData()


def get_table(name):
    return Table(name, metadata, autoload_with=engine)


# await conn.execute(
#         text(
#             f"INSERT INTO {table_name} (timestamp, experiment_id, scalar_name, value, step, tags) VALUES ($1, $2, $3, $4, $5, $6)"
#         ),
#         request.timestamp,
#         experiment_id,
#         request.scalar_name,
#         request.value,
#         request.step,
#         json.dumps(request.tags),
#     )


@router.post("/log/{project_id}/{experiment_id}")
async def log_scalar(
    project_id: str,
    experiment_id: str,
    request: LogScalarRequestDTO,
    session: AsyncSession = Depends(get_async_session),
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
):

    table_name = safe_scalars_table_name(project_id)
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        microseconds=1000
    )
    await conn.execute(
        f"INSERT INTO {table_name} (timestamp, experiment_id, scalar_name, value, step, tags) VALUES ($1, $2, $3, $4, $5, $6)",
        timestamp,
        experiment_id,
        request.scalar_name,
        request.value,
        request.step,
        json.dumps(request.tags),
    )
    return {"status": "logged"}


@router.get("/get/{project_id}/{experiment_id}")
async def get_scalars(
    project_id: str,
    experiment_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    print(db)
    print(f"Getting scalars for project {project_id} and experiment {experiment_id}")
