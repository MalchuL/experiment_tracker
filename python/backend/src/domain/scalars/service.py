from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, Sequence
from uuid import UUID

from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from .client import ScalarsClientProtocol, ScalarsServiceClient  # noqa: F401
from .error import ScalarsNotAccessibleError


def _as_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class ScalarsServiceProtocol(Protocol):
    async def create_project_table(self, project_id: UUID) -> dict[str, Any]: ...

    async def log_scalar(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def log_scalars_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def get_scalars(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]: ...

    async def get_scalars_for_experiment(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]: ...

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
    ) -> dict[str, Any]: ...


class ScalarsService:
    def __init__(
        self,
        client: ScalarsClientProtocol,
        permission_checker: PermissionChecker,
        experiment_repository: ExperimentRepository,
    ):
        self.client = client
        self.permission_checker = permission_checker
        self.experiment_repository = experiment_repository

    async def create_project_table(self, project_id: UUID) -> dict[str, Any]:
        return await self.client.create_project_table(project_id)

    async def log_scalar(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self.permission_checker.can_log_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to log scalars in project {project_id}"
            )
        result = await self.client.log_scalar(project_id, experiment_id, payload)
        return result

    async def log_scalars_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self.permission_checker.can_log_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to log scalars in project {project_id}"
            )
        result = await self.client.log_scalars_batch(project_id, experiment_id, payload)
        return result

    async def get_scalars(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
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
            project_id=project_id,
            experiment_ids=experiment_ids,
            max_points=max_points,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
        )

    async def get_scalars_for_experiment(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        return await self.get_scalars(
            user=user,
            project_id=project_id,
            experiment_ids=[experiment_id],
            max_points=max_points,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
        )

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
    ) -> dict[str, Any]:
        if not await self.permission_checker.can_view_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to view scalars in project {project_id}"
            )
        payload = (
            {"experiment_ids": None}
            if experiment_ids is None
            else {"experiment_ids": [str(experiment_id) for experiment_id in experiment_ids]}
        )
        return await self.client.get_last_logged_experiments(project_id, payload)


class NoOpScalarsService:
    async def create_project_table(self, project_id: UUID) -> dict[str, Any]:
        return {}

    async def log_scalar(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def log_scalars_batch(
        self, user: UserProtocol, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def get_scalars(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        return {"data": []}

    async def get_scalars_for_experiment(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        return {"data": []}

    async def get_last_logged_experiments(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
    ) -> dict[str, Any]:
        return {"data": []}
