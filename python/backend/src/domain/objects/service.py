from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, Sequence
from uuid import UUID

from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from .client import ObjectsClientProtocol, ObjectsServiceClient  # noqa: F401
from .error import ObjectsNotAccessibleError


def _as_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class ObjectsServiceProtocol(Protocol):
    async def log_object(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def log_objects_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def get_objects(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        object_types: Sequence[str] | None = None,
        names: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]: ...


class ObjectsService:
    def __init__(
        self,
        client: ObjectsClientProtocol,
        permission_checker: PermissionChecker,
        experiment_repository: ExperimentRepository,
    ):
        self.client = client
        self.permission_checker = permission_checker
        self.experiment_repository = experiment_repository

    async def log_object(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        # Resolve project through experiment, so API caller only provides experiment_id.
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        # Reuse scalar logging permission model for object logging.
        if not await self.permission_checker.can_log_scalar(user.id, project_id):
            raise ObjectsNotAccessibleError(
                f"You are not allowed to log objects in project {project_id}"
            )
        # Backend does authorization/orchestration and forwards persistence to scalars_service.
        return await self.client.log_object(project_id, experiment_id, payload)

    async def log_objects_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self.permission_checker.can_log_scalar(user.id, project_id):
            raise ObjectsNotAccessibleError(
                f"You are not allowed to log objects in project {project_id}"
            )
        return await self.client.log_objects_batch(project_id, experiment_id, payload)

    async def get_objects(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        object_types: Sequence[str] | None = None,
        names: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        if not await self.permission_checker.can_view_scalar(user.id, project_id):
            raise ObjectsNotAccessibleError(
                f"You are not allowed to view objects in project {project_id}"
            )
        if experiment_ids:
            # Validate that requested experiments exist and belong to the same project.
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
        return await self.client.get_objects(
            project_id=project_id,
            experiment_ids=experiment_ids,
            object_types=object_types,
            names=names,
            start_time=start_time,
            end_time=end_time,
        )


class NoOpObjectsService:
    async def log_object(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def log_objects_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def get_objects(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        object_types: Sequence[str] | None = None,
        names: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        return {"data": []}
