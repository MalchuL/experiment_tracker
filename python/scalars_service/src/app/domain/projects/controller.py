from config import get_settings
from db.utils import build_async_asyncpg_url
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional, Dict
from datetime import datetime
import io
from db.questdb import engine, get_async_session, get_asyncpg_connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from .dto import (
    CreateProjectTableDTO,
    CreateProjectTableResponseDTO,
    DeleteProjectTableResponseDTO,
    GetProjectTableExistenceDTO,
)
import asyncpg


import re


router = APIRouter(prefix="/projects", tags=["projects"])


def safe_scalars_table_name(project_id: str) -> str:
    """
    Валидируем имя таблицы: только латиница, цифры, нижнее подчеркивание.
    Должно начинаться с буквы или нижнего подчеркивания.
    """
    name = f"scalars_{project_id}".lower()
    if not re.match(r"^[a-z_][a-z0-9_]{1,63}$", name):
        raise HTTPException(status_code=400, detail="Invalid project_id")
    return name


@router.post("")
async def create_project_scalars_table(
    request: CreateProjectTableDTO,
    db: AsyncSession = Depends(get_async_session),
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
):
    table_name = safe_scalars_table_name(request.project_id)

    ddl = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        timestamp   TIMESTAMP NOT NULL,
        experiment_id SYMBOL,
        scalar_name   SYMBOL,
        value         DOUBLE NOT NULL,
        step          INT,
        tags          STRING
    ) TIMESTAMP(timestamp) PARTITION BY DAY;
    """
    # Create table for the provided project ID in the database using SQLAlchemy's metadata
    try:
        await conn.execute(ddl)
        return CreateProjectTableResponseDTO(
            table_name=table_name, project_id=request.project_id
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating table: {str(e)}")


@router.get("/exists/{project_id}")
async def get_project_table_existence(
    project_id: str,
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
):
    table_name = safe_scalars_table_name(project_id)
    try:
        await conn.fetch(f"SHOW CREATE TABLE {table_name}")
        return GetProjectTableExistenceDTO(
            table_name=table_name, project_id=project_id, exists=True
        )
    except asyncpg.UnknownPostgresError as e:
        return GetProjectTableExistenceDTO(
            table_name=table_name, project_id=project_id, exists=False
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking table existence: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project_table(
    project_id: str,
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
):
    table_name = safe_scalars_table_name(project_id)
    try:
        await conn.execute(f"DROP TABLE {table_name}")
        return DeleteProjectTableResponseDTO(
            message=f"Table {table_name} deleted successfully."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting table: {str(e)}")
