"""Last logged experiments service - shared by scalars and objects domains."""

from datetime import datetime
from typing import cast
from uuid import UUID

from experiment_tracker_shared import utc_naive_for_clickhouse_insert, utc_now_naive
from experiment_tracker_shared.datetime_utc import to_json_utc_z

from app.domain.projects.dto import ClickhouseTableUsageStats  # type: ignore
from app.domain.last_logged.dto import (  # type: ignore
    LastLoggedExperimentDTO,
    LastLoggedExperimentsResultDTO,
)
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore
from app.domain.utils.scalars_select_sql import SCALARS_SELECT_SQL  # type: ignore


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
            last_modified = utc_now_naive()
        sql_ts = utc_naive_for_clickhouse_insert(last_modified)
        await self._ensure_table(project_id)
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        statement = SCALARS_DB_UTILS.build_upsert_last_logged_statement(
            table_name, experiment_id, sql_ts
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
                last_modified=to_json_utc_z(cast(datetime, row[1])),
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

    async def create_clickhouse_table(self, project_id: UUID) -> str:
        """Run DDL for this project's last_logged table (idempotent if DDL uses IF NOT EXISTS)."""
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        ddl = SCALARS_DB_UTILS.build_create_last_logged_table_statement(table_name)
        await self.client.command(ddl)
        return table_name

    async def drop_clickhouse_table(self, project_id: UUID) -> None:
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        await self.client.command(
            SCALARS_DB_UTILS.build_drop_table_statement(table_name)
        )

    async def delete_experiment_rows_if_table_exists(
        self, project_id: UUID, experiment_id: UUID
    ) -> None:
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        if not await self._table_exists(table_name):
            return
        await self.client.command(
            SCALARS_DB_UTILS.build_alter_delete_experiment_rows_statement(
                table_name=table_name,
                experiment_id=experiment_id,
                experiment_id_column="experiment_id",
            )
        )

    async def get_clickhouse_table_usage_stats(
        self, project_id: UUID
    ) -> ClickhouseTableUsageStats:
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        if not await self._table_exists(table_name):
            return ClickhouseTableUsageStats(
                table=table_name,
                exists=False,
                rows=0,
                columns=0,
                bytes=0,
            )
        rows_result = await self.client.query(
            SCALARS_SELECT_SQL.count_all_rows(table_name)
        )
        rows = int(rows_result.result_rows[0][0]) if rows_result.result_rows else 0
        columns_result = await self.client.query(
            SCALARS_DB_UTILS.build_describe_table_statement(table_name)
        )
        columns = len(columns_result.result_rows)
        bytes_result = await self.client.query(
            SCALARS_SELECT_SQL.sum_bytes_on_disk_active_parts(
                SCALARS_DB_UTILS.escape_sql_literal(table_name)
            )
        )
        bytes_on_disk = (
            int(bytes_result.result_rows[0][0]) if bytes_result.result_rows else 0
        )
        return ClickhouseTableUsageStats(
            table=table_name,
            exists=True,
            rows=rows,
            columns=columns,
            bytes=bytes_on_disk,
        )
