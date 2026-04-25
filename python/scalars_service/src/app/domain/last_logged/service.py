"""Last logged experiments service - shared by scalars and objects domains."""

from datetime import datetime, timezone
from typing import cast
from uuid import UUID

from app.domain.last_logged.dto import (  # type: ignore
    LastLoggedExperimentDTO,
    LastLoggedExperimentsResultDTO,
)
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore


def _get_now_datetime() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LastLoggedService:
    def __init__(self, client):
        self.client = client

    async def touch(
        self,
        project_id: UUID,
        experiment_id: UUID,
        last_modified: datetime | None = None,
    ) -> None:
        """Update last_logged for the experiment. Creates table if it does not exist."""
        if last_modified is None:
            last_modified = _get_now_datetime()
        await self._ensure_table(project_id)
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        statement = SCALARS_DB_UTILS.build_upsert_last_logged_statement(
            table_name, experiment_id, last_modified
        )
        await self.client.command(statement)

    async def get_last_logged_experiments(
        self,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> LastLoggedExperimentsResultDTO:
        """Get last logged experiments for a project.

        Args:
            project_id: The project ID.
            experiment_ids: List of experiment IDs to filter. If None, returns all
                experiments in the project.

        Returns:
            LastLoggedExperimentsResultDTO with last_modified per experiment.
        """
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        if not await self._table_exists(table_name):
            return LastLoggedExperimentsResultDTO(
                data=[],
                has_next=False,
                size=0,
                total=0,
            )
        query = SCALARS_DB_UTILS.build_select_last_logged_statement(
            table_name,
            experiment_ids=experiment_ids,
        )
        result = await self.client.query(query)
        data = [
            LastLoggedExperimentDTO(
                experiment_id=cast(UUID, row[0]),
                last_modified=cast(datetime, row[1]).isoformat(),
            )
            for row in result.result_rows
        ]
        total = len(data)
        page = data[offset : offset + limit]
        return LastLoggedExperimentsResultDTO(
            data=page,
            has_next=offset + len(page) < total,
            size=len(page),
            total=total,
        )

    async def _ensure_table(self, project_id: UUID) -> None:
        """Ensure the last_logged table exists. Create it if it does not."""
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        if not await self._table_exists(table_name):
            ddl = SCALARS_DB_UTILS.build_create_last_logged_table_statement(table_name)
            await self.client.command(ddl)

    async def _table_exists(self, table_name: str) -> bool:
        query = SCALARS_DB_UTILS.build_table_existence_statement(table_name)
        result = await self.client.query(query)
        return bool(result.result_rows[0][0])
