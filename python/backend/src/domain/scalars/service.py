from __future__ import annotations

from typing import Any, Iterable, Protocol

from config.settings import get_settings
from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from .client import ScalarsClientProtocol, ScalarsServiceClient
from .error import ScalarsNotAccessibleError


class ScalarsServiceProtocol(Protocol):
    async def create_project_table(self, project_id: str) -> dict[str, Any]: ...

    async def log_scalar(
        self, project_id: str, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def log_scalars_batch(
        self, project_id: str, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def get_scalars(
        self,
        project_id: str,
        experiment_ids: Iterable[str] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
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

    async def create_project_table(self, project_id: str) -> dict[str, Any]:
        return await self.client.create_project_table(project_id)

    async def log_scalar(
        self,
        user: UserProtocol,
        experiment_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = experiment.project_id
        if not await self.permission_checker.can_log_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to log scalars in project {project_id}"
            )
        result = await self.client.log_scalar(project_id, experiment_id, payload)
        return result

    async def log_scalars_batch(
        self, user: UserProtocol, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        project_id = experiment.project_id
        if not await self.permission_checker.can_log_scalar(user.id, project_id):
            raise ScalarsNotAccessibleError(
                f"You are not allowed to log scalars in project {project_id}"
            )
        result = await self.client.log_scalars_batch(project_id, experiment_id, payload)
        return result

    async def get_scalars(
        self,
        user: UserProtocol,
        project_id: str | None = None,
        experiment_ids: Iterable[str] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
    ) -> dict[str, Any]:
        experiments = []
        if experiment_ids is not None:
            experiments.extend(
                await self.experiment_repository.get_experiments_by_ids(experiment_ids)
            )
        if project_id is not None:
            experiments.extend(
                await self.experiment_repository.get_experiments_by_project(project_id)
            )
        project_ids = set(experiment.project_id for experiment in experiments)
        results = []
        for project_id in project_ids:
            if not await self.permission_checker.can_view_scalar(user.id, project_id):
                raise ScalarsNotAccessibleError(
                    f"You are not allowed to view scalars in project {project_id}"
                )

            result = await self.client.get_scalars(
                project_id=project_id,
                experiment_ids=experiment_ids,
                max_points=max_points,
                return_tags=return_tags,
            )
            results.append(result)

        return results


class NoOpScalarsService:
    async def create_project_table(self, project_id: str) -> dict[str, Any]:
        return {}

    async def log_scalar(
        self, project_id: str, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def log_scalars_batch(
        self, project_id: str, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def get_scalars(
        self,
        project_id: str,
        experiment_ids: Iterable[str] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
    ) -> dict[str, Any]:
        return {}
