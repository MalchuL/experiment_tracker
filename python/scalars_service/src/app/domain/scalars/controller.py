from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional, Dict
from datetime import datetime
import io
from db.questdb import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession

from .dto import (
    LogScalarRequestDTO,
)

router = APIRouter(prefix="/scalars", tags=["scalars"])


@router.post("/log/{project_id}/{experiment_id}")
async def log_scalar(
    project_id: str,
    experiment_id: str,
    request: LogScalarRequestDTO,
):
    print(
        f"Logging scalar for project {project_id} and experiment {experiment_id} with request {request}"
    )


@router.get("/get/{project_id}/{experiment_id}")
async def get_scalars(
    project_id: str,
    experiment_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    print(db)
    print(f"Getting scalars for project {project_id} and experiment {experiment_id}")


async def create_project_table(
    project_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    print(db)
    print(f"Creating table for project {project_id}")
    await db.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {project_id}_scalars (id SERIAL PRIMARY KEY, name VARCHAR(255), value DOUBLE)"
        )
    )
    await db.commit()
