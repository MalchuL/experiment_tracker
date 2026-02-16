from uuid import UUID
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore
from .dto import (
    CreateProjectTableResponseDTO,
    DeleteProjectTableResponseDTO,
    GetProjectTableExistenceDTO,
)


class ProjectsService:
    def __init__(self, client):
        self.client = client

    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        last_logged_table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(
            project_id
        )
        scalars_ddl = SCALARS_DB_UTILS.build_create_scalars_table_statement(table_name)
        await self.client.command(scalars_ddl)
        last_logged_ddl = SCALARS_DB_UTILS.build_create_last_logged_table_statement(
            last_logged_table_name
        )
        await self.client.command(last_logged_ddl)
        return CreateProjectTableResponseDTO(
            table_name=table_name, project_id=project_id
        )

    async def get_project_table_existence(
        self, project_id: UUID
    ) -> GetProjectTableExistenceDTO:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        exists_query = SCALARS_DB_UTILS.build_table_existence_statement(table_name)
        exists = await self.client.query(exists_query)
        return GetProjectTableExistenceDTO(
            table_name=table_name,
            project_id=project_id,
            exists=bool(exists.result_rows[0][0]) if exists.result_rows else False,
        )

    async def get_project_experiments_ids(self, project_id: UUID) -> list[dict]:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        query = SCALARS_DB_UTILS.build_experiments_ids_statement(table_name)
        result = await self.client.query(query)
        return [{"experiment_id": row[0]} for row in result.result_rows]

    async def delete_project_table(
        self, project_id: UUID
    ) -> DeleteProjectTableResponseDTO:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        last_logged_table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(
            project_id
        )
        await self.client.command(
            SCALARS_DB_UTILS.build_delete_mapping_statement(project_id)
        )
        await self.client.command(
            SCALARS_DB_UTILS.build_drop_table_statement(table_name)
        )
        await self.client.command(
            SCALARS_DB_UTILS.build_drop_table_statement(last_logged_table_name)
        )
        return DeleteProjectTableResponseDTO(
            message=f"Table {table_name} deleted successfully."
        )
