"""Protocol for the scalars HTTP client used by ``ScalarsService`` in the main API."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .dto import (
    CreateProjectTableResponseDTO,
    GetScalarsResponseDTO,
    LastLoggedExperimentsRequestDTO,
    LastLoggedExperimentsResponseDTO,
    LogScalarsBatchRequestDTO,
    LogScalarRequestDTO,
    LogScalarResponseDTO,
    ScalarsCompactColumnsResponseDTO,
    ScalarsDeleteExperimentDataResponseDTO,
    ScalarsDeleteProjectTablesResponseDTO,
    ScalarsDropStorageTableResponseDTO,
    ScalarsExperimentUsageResponseDTO,
    ScalarsListStorageTablesResponseDTO,
    ScalarsProjectUsageResponseDTO,
    ScalarsQueryDTO,
)


class ScalarsClientProtocol(Protocol):
    """Low-level contract implemented by ``ScalarsServiceClient`` / ``NoOpScalarsServiceClient``.

    Methods mirror the scalars satellite: time-series logging/query plus project-scoped
    lifecycle (delete experiment rows, drop project tables, usage, admin table ops).
    """

    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO: ...

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO: ...

    async def log_scalars_batch(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO: ...

    async def get_scalars(self, query: ScalarsQueryDTO) -> GetScalarsResponseDTO: ...

    async def get_last_logged_experiments(
        self, project_id: UUID, payload: LastLoggedExperimentsRequestDTO
    ) -> LastLoggedExperimentsResponseDTO: ...

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO:
        """DELETE ``/projects/{project_id}/experiments/{experiment_id}`` on the satellite."""
        ...

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO:
        """DELETE ``/projects/{project_id}`` — drop all ClickHouse tables for the project."""
        ...

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO:
        """POST compaction for orphaned metric columns on the project's scalars table."""
        ...

    async def get_project_usage(self, project_id: UUID) -> ScalarsProjectUsageResponseDTO:
        """GET ClickHouse usage breakdown (bytes, per-table stats) for ``project_id``."""
        ...

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO:
        """GET bytes/row estimates for one experiment within the project's ClickHouse data."""
        ...

    async def list_storage_tables(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ScalarsListStorageTablesResponseDTO:
        """GET admin paginated list of managed scalars-related tables."""
        ...

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO:
        """DELETE admin route to drop a single managed table by name."""
        ...
