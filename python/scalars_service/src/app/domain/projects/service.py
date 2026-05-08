from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore
from .dto import (
    ClickhouseTableUsageStatsDTO,
    CreateProjectTableResponseDTO,
    DeleteExperimentScalarsDataResponseDTO,
    DeleteProjectTableResponseDTO,
    DropManagedStorageTableResponseDTO,
    ExperimentClickhouseUsageResponseDTO,
    GetProjectTableExistenceDTO,
    ListStorageTablesResponseDTO,
    ProjectClickhouseUsageResponseDTO,
)

if TYPE_CHECKING:
    from app.domain.artifacts_info.service import ArtifactsInfoService
    from app.domain.last_logged.service import LastLoggedService
    from app.domain.scalars.service import ScalarsService


class ProjectsService:
    """Orchestrates ClickHouse project-level tables: scalars, artifacts_info, last_logged, mapping."""

    def __init__(
        self,
        scalars_service: ScalarsService,
        artifacts_info_service: ArtifactsInfoService,
        last_logged_service: LastLoggedService,
    ):
        self._scalars = scalars_service
        self._artifacts = artifacts_info_service
        self._last_logged = last_logged_service

    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO:
        """Create scalars, artifacts_info, and last_logged tables for a project."""
        table_name = await self._scalars.create_clickhouse_table(project_id)
        await self._artifacts.create_clickhouse_table(project_id)
        await self._last_logged.create_clickhouse_table(project_id)
        return CreateProjectTableResponseDTO(
            table_name=table_name, project_id=project_id
        )

    async def get_project_table_existence(
        self, project_id: UUID
    ) -> GetProjectTableExistenceDTO:
        """Check if the project's scalars table exists."""
        table_name, exists = await self._scalars.get_scalars_table_existence(project_id)
        return GetProjectTableExistenceDTO(
            table_name=table_name,
            project_id=project_id,
            exists=exists,
        )

    async def get_project_experiments_ids(self, project_id: UUID) -> list[dict]:
        return await self._scalars.list_experiment_ids_for_project(project_id)

    async def delete_project_table(
        self, project_id: UUID
    ) -> DeleteProjectTableResponseDTO:
        scalars_table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        await self._scalars.delete_scalar_mapping_for_project(project_id)
        await self._scalars.drop_clickhouse_table(project_id)
        await self._last_logged.drop_clickhouse_table(project_id)
        await self._artifacts.drop_clickhouse_table(project_id)
        return DeleteProjectTableResponseDTO(
            message=f"Table {scalars_table_name} deleted successfully."
        )

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> DeleteExperimentScalarsDataResponseDTO:
        """Delete all ClickHouse rows for one experiment across scalars, artifacts_info, last_logged.

        ClickHouse deletes are asynchronous mutations; the endpoint is intentionally
        idempotent so orchestration can safely retry after partial failures.
        """
        await self._scalars.delete_experiment_rows_if_table_exists(
            project_id, experiment_id
        )
        await self._artifacts.delete_experiment_rows_if_table_exists(
            project_id, experiment_id
        )
        await self._last_logged.delete_experiment_rows_if_table_exists(
            project_id, experiment_id
        )
        await self._scalars.compact_project_columns(project_id)
        await self._scalars.invalidate_cache_for_experiment(project_id, experiment_id)
        return DeleteExperimentScalarsDataResponseDTO(deleted=True)

    async def get_project_usage(
        self, project_id: UUID
    ) -> ProjectClickhouseUsageResponseDTO:
        """Return best-effort ClickHouse usage for a project's scalar-side tables."""
        table_rows = [
            await self._scalars.get_clickhouse_table_usage_stats(project_id),
            await self._artifacts.get_clickhouse_table_usage_stats(project_id),
            await self._last_logged.get_clickhouse_table_usage_stats(project_id),
        ]
        total_bytes = sum(row.bytes for row in table_rows)
        return ProjectClickhouseUsageResponseDTO(
            project_id=project_id,
            total_bytes=total_bytes,
            tables=[
                ClickhouseTableUsageStatsDTO(
                    table=row.table,
                    exists=row.exists,
                    rows=row.rows,
                    columns=row.columns,
                    bytes=row.bytes,
                )
                for row in table_rows
            ],
        )

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ExperimentClickhouseUsageResponseDTO:
        """Estimate scalar bytes for an experiment from its row share."""
        stats_three = [
            await self._scalars.get_clickhouse_table_usage_stats(project_id),
            await self._artifacts.get_clickhouse_table_usage_stats(project_id),
            await self._last_logged.get_clickhouse_table_usage_stats(project_id),
        ]
        return await self._scalars.get_experiment_usage_estimate(
            project_id, experiment_id, stats_three
        )

    async def list_storage_tables(
        self,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ListStorageTablesResponseDTO:
        """Admin/debug list of scalar-service tables relevant to storage cleanup."""
        return await self._scalars.list_admin_storage_tables(
            q=q, limit=limit, offset=offset
        )

    async def drop_table(self, table_name: str) -> DropManagedStorageTableResponseDTO:
        if not table_name.startswith(("scalars_", "artifacts_info_")):
            raise ValueError("Only scalar-service managed tables can be dropped")
        if not table_name.replace("_", "").isalnum():
            raise ValueError("Invalid table name")
        if table_name.startswith("scalars_"):
            await self._scalars.drop_managed_table_by_name(table_name)
        else:
            await self._artifacts.drop_managed_table_by_name(table_name)
        return DropManagedStorageTableResponseDTO(dropped=True, table=table_name)
