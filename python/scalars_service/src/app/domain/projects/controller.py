from fastapi import APIRouter, HTTPException, Depends
from db.questdb import get_async_session, get_asyncpg_connection
from sqlalchemy.ext.asyncio import AsyncSession

from .dto import (
    CreateProjectTableDTO,
    CreateProjectTableResponseDTO,
    DeleteProjectTableResponseDTO,
    GetProjectTableExistenceDTO,
)
import asyncpg
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("")
async def create_project_scalars_table(
    request: CreateProjectTableDTO,
    db: AsyncSession = Depends(get_async_session),
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
):
    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(request.project_id)

    ddl = SCALARS_DB_UTILS.build_create_table_statement(table_name)
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
    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    try:
        await conn.fetch(SCALARS_DB_UTILS.check_table_existence(table_name))
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


@router.get("/experiments/{project_id}")
async def get_project_experiments_ids(
    project_id: str,
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
):
    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    try:
        return await conn.fetch(SCALARS_DB_UTILS.get_experiments_ids(table_name))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting experiments IDs: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project_table(
    project_id: str,
    conn: asyncpg.Connection = Depends(get_asyncpg_connection),
):
    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    try:
        await conn.execute(SCALARS_DB_UTILS.build_drop_table_statement(table_name))
        return DeleteProjectTableResponseDTO(
            message=f"Table {table_name} deleted successfully."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting table: {str(e)}")
