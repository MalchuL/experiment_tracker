"""Scalars satellite facade: HTTP client to the scalars service plus RBAC on experiments/projects."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence
from uuid import UUID

from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from clients.scalars import (
    CreateProjectTableResponseDTO,
    GetScalarsResponseDTO,
    LastLoggedExperimentsRequestDTO,
    LastLoggedExperimentsResponseDTO,
    LogScalarsBatchRequestDTO,
    LogScalarRequestDTO,
    LogScalarResponseDTO,
    ScalarsClientProtocol,
    ScalarsCompactColumnsResponseDTO,
    ScalarsDeleteExperimentDataResponseDTO,
    ScalarsDeleteProjectTablesResponseDTO,
    ScalarsDropStorageTableResponseDTO,
    ScalarsExperimentUsageResponseDTO,
    ScalarsListStorageTablesResponseDTO,
    ScalarsProjectUsageResponseDTO,
    ScalarsQueryDTO,
    ScalarsSampling,
)
from lib.pagination import ListOptions
from .error import ScalarsNotAccessibleError


def _as_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class ScalarsServiceProtocol(Protocol):
    """Contract implemented by ``ScalarsService`` and ``NoOpScalarsService``.

    Split responsibilities:
    - **User-scoped** read/write (``log_scalar``, ``get_scalars``, …) enforce RBAC via
      ``ScalarsService`` using the experiment repository and permission checker.
    - **Project-scoped satellite ops** (delete rows/tables, usage, admin list/drop) are
      forwarded without per-user checks here; callers in ``ExperimentService`` /
      ``ProjectService`` / admin routes must enforce permissions first.
    """

    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO: ...

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO: ...

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO: ...

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO: ...

    async def get_project_usage(
        self, project_id: UUID
    ) -> ScalarsProjectUsageResponseDTO: ...

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO: ...

    async def list_storage_tables(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ScalarsListStorageTablesResponseDTO: ...

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO: ...

    async def log_scalar(
        self, user: UserProtocol, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO: ...

    async def log_scalars_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO: ...

    async def get_scalars(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
        max_points: int | None = None,
        sampling: ScalarsSampling = ScalarsSampling.UNIFORM,
        columns_per_query: int = 1,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> GetScalarsResponseDTO: ...

    async def get_scalars_for_experiment(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        list_options: ListOptions = ListOptions(),
        max_points: int | None = None,
        sampling: ScalarsSampling = ScalarsSampling.UNIFORM,
        columns_per_query: int = 1,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> GetScalarsResponseDTO: ...

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
    ) -> LastLoggedExperimentsResponseDTO: ...


class ScalarsService:
    """Production implementation: forwards to ``ScalarsClientProtocol`` after permission checks.

    RBAC applies to **scalar read/write** paths that accept a ``user``. Methods that only
    take ``project_id`` / ``experiment_id`` are thin HTTP forwards used after the main
    API has already verified delete/view-project rights.
    """

    def __init__(
        self,
        client: ScalarsClientProtocol,
        permission_checker: PermissionChecker,
        experiment_repository: ExperimentRepository,
    ):
        self.client = client
        self.permission_checker = permission_checker
        self.experiment_repository = experiment_repository

    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO:
        """Provision ClickHouse tables for a new project (called from ``ProjectService``)."""
        return await self.client.create_project_table(project_id)

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO:
        """Delegate full ClickHouse cleanup for one experiment to the scalars satellite."""
        return await self.client.delete_experiment_data(project_id, experiment_id)

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO:
        """Drop all per-project ClickHouse tables when the project is removed from Postgres."""
        return await self.client.delete_project_table(project_id)

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO:
        """Optional maintenance: remove unused metric columns after deletes."""
        return await self.client.compact_project_columns(project_id)

    async def get_project_usage(
        self, project_id: UUID
    ) -> ScalarsProjectUsageResponseDTO:
        """Return satellite usage DTO for ClickHouse-side bytes and per-table stats."""
        return await self.client.get_project_usage(project_id)

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO:
        """Return satellite usage DTO for one experiment's ClickHouse footprint."""
        return await self.client.get_experiment_usage(project_id, experiment_id)

    async def list_storage_tables(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ScalarsListStorageTablesResponseDTO:
        """Admin: list managed ClickHouse tables (used from ``/admin/storage/scalars``)."""
        return await self.client.list_storage_tables(q=q, limit=limit, offset=offset)

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO:
        """Admin: drop a named managed table in ClickHouse."""
        return await self.client.drop_storage_table(table_name)

    async def log_scalar(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        payload: LogScalarRequestDTO,
    ) -> LogScalarResponseDTO:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self.permission_checker.can_log_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to log scalars in project {project_id}"
            )
        return await self.client.log_scalar(project_id, experiment_id, payload)

    async def log_scalars_batch(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        payload: LogScalarsBatchRequestDTO,
    ) -> LogScalarResponseDTO:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self.permission_checker.can_log_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to log scalars in project {project_id}"
            )
        return await self.client.log_scalars_batch(
            project_id, experiment_id, payload
        )

    async def get_scalars(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
        max_points: int | None = None,
        sampling: ScalarsSampling = ScalarsSampling.UNIFORM,
        columns_per_query: int = 1,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> GetScalarsResponseDTO:
        if not await self.permission_checker.can_view_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to view scalars in project {project_id}"
            )

        if experiment_ids:
            experiments = await self.experiment_repository.get_experiments_by_ids(
                list(experiment_ids)
            )
            found_experiment_ids = {experiment.id for experiment in experiments}
            invalid_ids = {
                experiment_id
                for experiment_id in experiment_ids
                if experiment_id not in found_experiment_ids
            }
            if invalid_ids:
                invalid_text = ", ".join(str(experiment_id) for experiment_id in invalid_ids)
                raise ValueError(f"Experiments not found: {invalid_text}")
            foreign_project_ids = {
                _as_uuid(experiment.project_id)
                for experiment in experiments
                if _as_uuid(experiment.project_id) != project_id
            }
            if foreign_project_ids:
                raise ValueError(
                    "All experiment_ids must belong to the specified project_id"
                )

        return await self.client.get_scalars(
            ScalarsQueryDTO(
                project_id=project_id,
                experiment_ids=list(experiment_ids) if experiment_ids else None,
                limit=list_options.limit,
                offset=list_options.offset,
                max_points=max_points,
                sampling=sampling,
                columns_per_query=columns_per_query,
                return_tags=return_tags,
                start_time=start_time,
                end_time=end_time,
            )
        )

    async def get_scalars_for_experiment(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        list_options: ListOptions = ListOptions(),
        max_points: int | None = None,
        sampling: ScalarsSampling = ScalarsSampling.UNIFORM,
        columns_per_query: int = 1,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> GetScalarsResponseDTO:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        return await self.get_scalars(
            user=user,
            project_id=project_id,
            experiment_ids=[experiment_id],
            list_options=list_options,
            max_points=max_points,
            sampling=sampling,
            columns_per_query=columns_per_query,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
        )

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
    ) -> LastLoggedExperimentsResponseDTO:
        if not await self.permission_checker.can_view_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to view scalars in project {project_id}"
            )
        payload = LastLoggedExperimentsRequestDTO(
            experiment_ids=list(experiment_ids) if experiment_ids else None
        )
        return await self.client.get_last_logged_experiments(
            project_id,
            payload,
            limit=list_options.limit,
            offset=list_options.offset,
        )


class NoOpScalarsService:
    """Stub satellite for tests or deployments without scalars: no-op or empty payloads.

    Implements the same surface as ``ScalarsService`` so dependency injection does not
    branch on ``None``; delete/usage paths return benign DTO-shaped values.
    """

    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO:
        return CreateProjectTableResponseDTO(table_name="", project_id=project_id)

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO:
        _ = (project_id, experiment_id)
        return ScalarsDeleteExperimentDataResponseDTO(deleted=True)

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO:
        _ = project_id
        return ScalarsDeleteProjectTablesResponseDTO(message="noop")

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO:
        _ = project_id
        return ScalarsCompactColumnsResponseDTO(dropped_columns=[])

    async def get_project_usage(
        self, project_id: UUID
    ) -> ScalarsProjectUsageResponseDTO:
        return ScalarsProjectUsageResponseDTO(
            project_id=project_id, total_bytes=0, tables=[]
        )

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO:
        return ScalarsExperimentUsageResponseDTO(
            project_id=project_id,
            experiment_id=experiment_id,
            bytes=0,
            rows=0,
        )

    async def list_storage_tables(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ScalarsListStorageTablesResponseDTO:
        _ = q
        return ScalarsListStorageTablesResponseDTO(
            tables=[], total=0, limit=limit, offset=offset
        )

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO:
        return ScalarsDropStorageTableResponseDTO(dropped=True, table=table_name)

    async def log_scalar(
        self, user: UserProtocol, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO:
        _ = (user, experiment_id, payload)
        return LogScalarResponseDTO(status="noop")

    async def log_scalars_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO:
        _ = (user, experiment_id, payload)
        return LogScalarResponseDTO(status="noop")

    async def get_scalars(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
        max_points: int | None = None,
        sampling: ScalarsSampling = ScalarsSampling.UNIFORM,
        columns_per_query: int = 1,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> GetScalarsResponseDTO:
        _ = (
            user,
            project_id,
            experiment_ids,
            list_options,
            max_points,
            sampling,
            columns_per_query,
            return_tags,
            start_time,
            end_time,
        )
        return GetScalarsResponseDTO(data=[], has_next=False, size=0, total=0)

    async def get_scalars_for_experiment(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        list_options: ListOptions = ListOptions(),
        max_points: int | None = None,
        sampling: ScalarsSampling = ScalarsSampling.UNIFORM,
        columns_per_query: int = 1,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> GetScalarsResponseDTO:
        _ = (
            user,
            experiment_id,
            list_options,
            max_points,
            sampling,
            columns_per_query,
            return_tags,
            start_time,
            end_time,
        )
        return GetScalarsResponseDTO(data=[], has_next=False, size=0, total=0)

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
    ) -> LastLoggedExperimentsResponseDTO:
        _ = (user, project_id, experiment_ids, list_options)
        return LastLoggedExperimentsResponseDTO(data=[], has_next=False, size=0, total=0)
