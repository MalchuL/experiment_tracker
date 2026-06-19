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
    ScalarNamesResponseDTO,
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
    ) -> CreateProjectTableResponseDTO:
        """Create scalars storage for a project.

        Args:
            project_id: Project identifier.

        Returns:
            CreateProjectTableResponseDTO: Table creation result.
        """
        ...

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO:
        """Delete scalar-side rows for one experiment.

        Args:
            project_id: Project identifier.
            experiment_id: Experiment identifier.

        Returns:
            ScalarsDeleteExperimentDataResponseDTO: Cleanup result.
        """
        ...

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO:
        """Drop scalars storage for a project.

        Args:
            project_id: Project identifier.

        Returns:
            ScalarsDeleteProjectTablesResponseDTO: Table deletion result.
        """
        ...

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO:
        """Compact unused scalars columns for a project.

        Args:
            project_id: Project identifier.

        Returns:
            ScalarsCompactColumnsResponseDTO: Dropped-column summary.
        """
        ...

    async def get_project_usage(
        self, project_id: UUID
    ) -> ScalarsProjectUsageResponseDTO:
        """Return scalar storage usage for a project.

        Args:
            project_id: Project identifier.

        Returns:
            ScalarsProjectUsageResponseDTO: Project usage summary.
        """
        ...

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO:
        """Return scalar storage usage for one experiment.

        Args:
            project_id: Project identifier.
            experiment_id: Experiment identifier.

        Returns:
            ScalarsExperimentUsageResponseDTO: Experiment usage summary.
        """
        ...

    async def list_storage_tables(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ScalarsListStorageTablesResponseDTO:
        """List managed scalars storage tables.

        Args:
            q: Optional table-name filter.
            limit: Maximum number of rows.
            offset: Number of rows to skip.

        Returns:
            ScalarsListStorageTablesResponseDTO: Paginated table metadata.
        """
        ...

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO:
        """Drop a managed scalars storage table.

        Args:
            table_name: Table name to drop.

        Returns:
            ScalarsDropStorageTableResponseDTO: Drop result.
        """
        ...

    async def log_scalar(
        self, user: UserProtocol, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO:
        """Log one scalar point.

        Args:
            user: User logging the scalar.
            experiment_id: Experiment identifier.
            payload: Scalar payload.

        Returns:
            LogScalarResponseDTO: Logging result.
        """
        ...

    async def log_scalars_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO:
        """Log a batch of scalar points.

        Args:
            user: User logging scalars.
            experiment_id: Experiment identifier.
            payload: Batch scalar payload.

        Returns:
            LogScalarResponseDTO: Logging result.
        """
        ...

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
        start_step: int | None = None,
        end_step: int | None = None,
        scalar_names: Sequence[str] | None = None,
        store_cache: bool = True,
    ) -> GetScalarsResponseDTO:
        """Query scalar series for a project.

        Args:
            user: User requesting scalar data.
            project_id: Project identifier.
            experiment_ids: Optional experiment filter.
            list_options: Pagination limit and offset.
            max_points: Optional sampling target.
            sampling: Sampling strategy.
            columns_per_query: Column query parallelism.
            return_tags: Whether to include tags.
            start_time: Optional lower timestamp bound.
            end_time: Optional upper timestamp bound.

        Returns:
            GetScalarsResponseDTO: Scalar query response.
        """
        ...

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
        start_step: int | None = None,
        end_step: int | None = None,
        scalar_names: Sequence[str] | None = None,
        store_cache: bool = True,
    ) -> GetScalarsResponseDTO:
        """Query scalar series for one experiment.

        Args:
            user: User requesting scalar data.
            experiment_id: Experiment identifier.
            list_options: Pagination limit and offset.
            max_points: Optional sampling target.
            sampling: Sampling strategy.
            columns_per_query: Column query parallelism.
            return_tags: Whether to include tags.
            start_time: Optional lower timestamp bound.
            end_time: Optional upper timestamp bound.

        Returns:
            GetScalarsResponseDTO: Scalar query response.
        """
        ...

    async def get_scalar_names(
        self,
        user: UserProtocol,
        project_id: UUID,
    ) -> ScalarNamesResponseDTO:
        """Return known scalar names for a project."""
        ...

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
    ) -> LastLoggedExperimentsResponseDTO:
        """Return last-logged scalar metadata for project experiments.

        Args:
            user: User requesting metadata.
            project_id: Project identifier.
            experiment_ids: Optional experiment filter.
            list_options: Pagination limit and offset.

        Returns:
            LastLoggedExperimentsResponseDTO: Last-logged metadata response.
        """
        ...


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
        """Provision ClickHouse tables for a new project.

        Args:
            project_id: Project identifier.

        Returns:
            CreateProjectTableResponseDTO: Satellite table creation result.

        Raises:
            httpx.HTTPError: Propagated by the scalars client on upstream failures.
        """
        return await self.client.create_project_table(project_id)

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO:
        """Delete all scalar-side data for one experiment.

        Args:
            project_id: Project that owns the experiment tables.
            experiment_id: Experiment whose rows should be removed.

        Returns:
            ScalarsDeleteExperimentDataResponseDTO: Satellite cleanup result.

        Raises:
            httpx.HTTPError: Propagated by the scalars client.
        """
        return await self.client.delete_experiment_data(project_id, experiment_id)

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO:
        """Drop all scalars tables for a project.

        Args:
            project_id: Project whose managed tables should be dropped.

        Returns:
            ScalarsDeleteProjectTablesResponseDTO: Satellite table deletion result.

        Raises:
            httpx.HTTPError: Propagated by the scalars client.
        """
        return await self.client.delete_project_table(project_id)

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO:
        """Compact unused metric columns for a project.

        Args:
            project_id: Project whose scalar columns should be compacted.

        Returns:
            ScalarsCompactColumnsResponseDTO: Dropped-column summary.

        Raises:
            httpx.HTTPError: Propagated by the scalars client.
        """
        return await self.client.compact_project_columns(project_id)

    async def get_project_usage(
        self, project_id: UUID
    ) -> ScalarsProjectUsageResponseDTO:
        """Return ClickHouse usage for a project.

        Args:
            project_id: Project identifier.

        Returns:
            ScalarsProjectUsageResponseDTO: Total bytes and table-level usage stats.

        Raises:
            httpx.HTTPError: Propagated by the scalars client.
        """
        return await self.client.get_project_usage(project_id)

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO:
        """Return ClickHouse usage for one experiment.

        Args:
            project_id: Project identifier.
            experiment_id: Experiment identifier.

        Returns:
            ScalarsExperimentUsageResponseDTO: Experiment row and byte usage.

        Raises:
            httpx.HTTPError: Propagated by the scalars client.
        """
        return await self.client.get_experiment_usage(project_id, experiment_id)

    async def list_storage_tables(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ScalarsListStorageTablesResponseDTO:
        """List managed ClickHouse tables for admin storage views.

        Args:
            q: Optional table-name filter.
            limit: Maximum number of tables to return.
            offset: Number of tables to skip.

        Returns:
            ScalarsListStorageTablesResponseDTO: Paginated table metadata.

        Raises:
            httpx.HTTPError: Propagated by the scalars client.
        """
        return await self.client.list_storage_tables(q=q, limit=limit, offset=offset)

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO:
        """Drop one managed ClickHouse table by name.

        Args:
            table_name: Managed table name to drop.

        Returns:
            ScalarsDropStorageTableResponseDTO: Drop result.

        Raises:
            httpx.HTTPError: Propagated by the scalars client.
        """
        return await self.client.drop_storage_table(table_name)

    async def log_scalar(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        payload: LogScalarRequestDTO,
    ) -> LogScalarResponseDTO:
        """Log one scalar point after experiment-level permission resolution.

        Args:
            user: User logging the scalar.
            experiment_id: Experiment receiving the scalar row.
            payload: Scalar payload to forward to the satellite.

        Returns:
            LogScalarResponseDTO: Satellite logging result.

        Raises:
            ScalarsNotAccessibleError: If the user cannot log scalars in the project.
            DBNotFoundError: If the experiment repository cannot load the experiment.
            httpx.HTTPError: Propagated by the scalars client.
        """
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
        """Log multiple scalar points after permission resolution.

        Args:
            user: User logging scalars.
            experiment_id: Experiment receiving scalar rows.
            payload: Batch scalar payload.

        Returns:
            LogScalarResponseDTO: Satellite logging result.

        Raises:
            ScalarsNotAccessibleError: If the user cannot log scalars in the project.
            DBNotFoundError: If the experiment repository cannot load the experiment.
            httpx.HTTPError: Propagated by the scalars client.
        """
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
        start_step: int | None = None,
        end_step: int | None = None,
        scalar_names: Sequence[str] | None = None,
        store_cache: bool = True,
    ) -> GetScalarsResponseDTO:
        """Query scalar series for a project.

        Args:
            user: User requesting scalar data.
            project_id: Project whose scalars should be queried.
            experiment_ids: Optional experiment filter; all ids must exist in the
                project.
            list_options: Pagination limit and offset for experiment groups.
            max_points: Optional sampling target per metric column.
            sampling: Sampling algorithm for the satellite.
            columns_per_query: Column query parallelism hint.
            return_tags: Whether tag metadata should be included.
            start_time: Optional lower timestamp bound.
            end_time: Optional upper timestamp bound.

        Returns:
            GetScalarsResponseDTO: Paginated scalar series response.

        Raises:
            ScalarsNotAccessibleError: If the user cannot view scalars in the project.
            ValueError: If requested experiment ids are missing or belong to another
                project.
            httpx.HTTPError: Propagated by the scalars client.
        """
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
                start_step=start_step,
                end_step=end_step,
                scalar_names=list(scalar_names) if scalar_names is not None else None,
                store_cache=store_cache,
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
        start_step: int | None = None,
        end_step: int | None = None,
        scalar_names: Sequence[str] | None = None,
        store_cache: bool = True,
    ) -> GetScalarsResponseDTO:
        """Query scalar series for one experiment.

        Args:
            user: User requesting scalar data.
            experiment_id: Experiment identifier.
            list_options: Pagination limit and offset.
            max_points: Optional sampling target per metric column.
            sampling: Sampling algorithm for the satellite.
            columns_per_query: Column query parallelism hint.
            return_tags: Whether tag metadata should be included.
            start_time: Optional lower timestamp bound.
            end_time: Optional upper timestamp bound.

        Returns:
            GetScalarsResponseDTO: Scalar series response constrained to the
            experiment.

        Raises:
            ScalarsNotAccessibleError: If the user cannot view scalars in the
                experiment's project.
            DBNotFoundError: If the experiment repository cannot load the experiment.
            httpx.HTTPError: Propagated by the scalars client.
        """
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
            start_step=start_step,
            end_step=end_step,
            scalar_names=scalar_names,
            store_cache=store_cache,
        )

    async def get_scalar_names(
        self,
        user: UserProtocol,
        project_id: UUID,
    ) -> ScalarNamesResponseDTO:
        if not await self.permission_checker.can_view_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to view scalars in project {project_id}"
            )
        return await self.client.get_scalar_names(project_id)

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
    ) -> LastLoggedExperimentsResponseDTO:
        """Return last-logged scalar metadata for experiments in a project.

        Args:
            user: User requesting metadata.
            project_id: Project identifier.
            experiment_ids: Optional experiment filter.
            list_options: Pagination limit and offset.

        Returns:
            LastLoggedExperimentsResponseDTO: Paginated last-logged experiment rows.

        Raises:
            ScalarsNotAccessibleError: If the user cannot view scalars in the project.
            httpx.HTTPError: Propagated by the scalars client.
        """
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
        """Return a benign project-table creation result.

        Args:
            project_id: Project identifier to echo in the response.

        Returns:
            CreateProjectTableResponseDTO: Empty table name with the project id.
        """
        return CreateProjectTableResponseDTO(table_name="", project_id=project_id)

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO:
        """Return a successful no-op experiment cleanup result.

        Args:
            project_id: Ignored project id.
            experiment_id: Ignored experiment id.

        Returns:
            ScalarsDeleteExperimentDataResponseDTO: Benign deleted status.
        """
        _ = (project_id, experiment_id)
        return ScalarsDeleteExperimentDataResponseDTO(deleted=True)

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO:
        """Return a successful no-op project table deletion result.

        Args:
            project_id: Ignored project id.

        Returns:
            ScalarsDeleteProjectTablesResponseDTO: Benign no-op message.
        """
        _ = project_id
        return ScalarsDeleteProjectTablesResponseDTO(message="noop")

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO:
        """Return an empty compaction result.

        Args:
            project_id: Ignored project id.

        Returns:
            ScalarsCompactColumnsResponseDTO: Empty dropped-column list.
        """
        _ = project_id
        return ScalarsCompactColumnsResponseDTO(dropped_columns=[])

    async def get_project_usage(
        self, project_id: UUID
    ) -> ScalarsProjectUsageResponseDTO:
        """Return zero scalar usage for a project.

        Args:
            project_id: Project identifier to echo in the response.

        Returns:
            ScalarsProjectUsageResponseDTO: Zero-byte usage with no tables.
        """
        return ScalarsProjectUsageResponseDTO(
            project_id=project_id, total_bytes=0, tables=[]
        )

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO:
        """Return zero scalar usage for an experiment.

        Args:
            project_id: Project identifier to echo in the response.
            experiment_id: Experiment identifier to echo in the response.

        Returns:
            ScalarsExperimentUsageResponseDTO: Zero-byte and zero-row usage.
        """
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
        """Return an empty managed-table page.

        Args:
            q: Ignored table-name filter.
            limit: Limit echoed in the response.
            offset: Offset echoed in the response.

        Returns:
            ScalarsListStorageTablesResponseDTO: Empty table list.
        """
        _ = q
        return ScalarsListStorageTablesResponseDTO(
            tables=[], total=0, limit=limit, offset=offset
        )

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO:
        """Return a successful no-op table drop result.

        Args:
            table_name: Table name echoed in the response.

        Returns:
            ScalarsDropStorageTableResponseDTO: Benign dropped status.
        """
        return ScalarsDropStorageTableResponseDTO(dropped=True, table=table_name)

    async def log_scalar(
        self, user: UserProtocol, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO:
        """Return a benign scalar logging result.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            payload: Ignored scalar payload.

        Returns:
            LogScalarResponseDTO: ``noop`` status.
        """
        _ = (user, experiment_id, payload)
        return LogScalarResponseDTO(status="noop")

    async def log_scalars_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO:
        """Return a benign batch scalar logging result.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            payload: Ignored batch payload.

        Returns:
            LogScalarResponseDTO: ``noop`` status.
        """
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
        start_step: int | None = None,
        end_step: int | None = None,
        scalar_names: Sequence[str] | None = None,
        store_cache: bool = True,
    ) -> GetScalarsResponseDTO:
        """Return an empty scalar query response.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            experiment_ids: Ignored experiment filter.
            list_options: Ignored pagination options.
            max_points: Ignored sampling target.
            sampling: Ignored sampling strategy.
            columns_per_query: Ignored query parallelism.
            return_tags: Ignored tag flag.
            start_time: Ignored lower timestamp bound.
            end_time: Ignored upper timestamp bound.

        Returns:
            GetScalarsResponseDTO: Empty page.
        """
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
            start_step,
            end_step,
            scalar_names,
            store_cache,
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
        start_step: int | None = None,
        end_step: int | None = None,
        scalar_names: Sequence[str] | None = None,
        store_cache: bool = True,
    ) -> GetScalarsResponseDTO:
        """Return an empty scalar query response for one experiment.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            list_options: Ignored pagination options.
            max_points: Ignored sampling target.
            sampling: Ignored sampling strategy.
            columns_per_query: Ignored query parallelism.
            return_tags: Ignored tag flag.
            start_time: Ignored lower timestamp bound.
            end_time: Ignored upper timestamp bound.

        Returns:
            GetScalarsResponseDTO: Empty page.
        """
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
            start_step,
            end_step,
            scalar_names,
            store_cache,
        )
        return GetScalarsResponseDTO(data=[], has_next=False, size=0, total=0)

    async def get_scalar_names(
        self,
        user: UserProtocol,
        project_id: UUID,
    ) -> ScalarNamesResponseDTO:
        _ = (user, project_id)
        return ScalarNamesResponseDTO(scalar_names=[])

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        list_options: ListOptions = ListOptions(),
    ) -> LastLoggedExperimentsResponseDTO:
        """Return an empty last-logged metadata response.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            experiment_ids: Ignored experiment filter.
            list_options: Pagination options whose limit/offset are ignored.

        Returns:
            LastLoggedExperimentsResponseDTO: Empty page.
        """
        _ = (user, project_id, experiment_ids, list_options)
        return LastLoggedExperimentsResponseDTO(data=[], has_next=False, size=0, total=0)
