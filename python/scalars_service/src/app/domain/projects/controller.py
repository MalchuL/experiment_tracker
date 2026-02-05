from fastapi import APIRouter, HTTPException, Depends
from db.clickhouse import get_clickhouse_client  # type: ignore

from .dto import (
    CreateProjectTableDTO,
    CreateProjectTableResponseDTO,
    DeleteProjectTableResponseDTO,
    GetProjectTableExistenceDTO,
)
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("")
async def create_project_scalars_table(
    request: CreateProjectTableDTO,
    client=Depends(get_clickhouse_client),
):
    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(request.project_id)

    ddl = SCALARS_DB_UTILS.build_create_table_statement(table_name)
    try:
        await client.command(ddl)
        return CreateProjectTableResponseDTO(
            table_name=table_name, project_id=request.project_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating table: {str(e)}")


@router.get("/exists/{project_id}")
async def get_project_table_existence(
    project_id: str,
    client=Depends(get_clickhouse_client),
):
    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    try:
        exists_query = SCALARS_DB_UTILS.build_table_existence_statement(table_name)
        exists = await client.query(exists_query)
        return GetProjectTableExistenceDTO(
            table_name=table_name,
            project_id=project_id,
            exists=bool(exists.result_rows[0][0]),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking table existence: {str(e)}"
        )


@router.get("/experiments/{project_id}")
async def get_project_experiments_ids(
    project_id: str,
    client=Depends(get_clickhouse_client),
):
    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    try:
        query = SCALARS_DB_UTILS.get_experiments_ids(table_name)
        result = await client.query(query)
        return [{"experiment_id": row[0]} for row in result.result_rows]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting experiments IDs: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project_table(
    project_id: str,
    client=Depends(get_clickhouse_client),
):
    table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    try:
        await client.command(SCALARS_DB_UTILS.build_drop_table_statement(table_name))
        return DeleteProjectTableResponseDTO(
            message=f"Table {table_name} deleted successfully."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting table: {str(e)}")
