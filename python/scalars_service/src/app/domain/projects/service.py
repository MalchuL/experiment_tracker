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
        self, project_id: str
    ) -> CreateProjectTableResponseDTO:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        ddl = SCALARS_DB_UTILS.build_create_table_statement(table_name)
        await self.client.command(ddl)
        return CreateProjectTableResponseDTO(
            table_name=table_name, project_id=project_id
        )

    async def get_project_table_existence(
        self, project_id: str
    ) -> GetProjectTableExistenceDTO:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        exists_query = SCALARS_DB_UTILS.build_table_existence_statement(table_name)
        exists = await self.client.query(exists_query)
        return GetProjectTableExistenceDTO(
            table_name=table_name,
            project_id=project_id,
            exists=bool(exists.result_rows[0][0]) if exists.result_rows else False,
        )

    async def get_project_experiments_ids(self, project_id: str) -> list[dict]:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        query = SCALARS_DB_UTILS.get_experiments_ids(table_name)
        result = await self.client.query(query)
        return [{"experiment_id": row[0]} for row in result.result_rows]

    async def delete_project_table(self, project_id: str) -> DeleteProjectTableResponseDTO:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        await self.client.command(SCALARS_DB_UTILS.build_drop_table_statement(table_name))
        return DeleteProjectTableResponseDTO(
            message=f"Table {table_name} deleted successfully."
        )
