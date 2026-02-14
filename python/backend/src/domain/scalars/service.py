from __future__ import annotations

from typing import Any, Iterable, Protocol

from config.settings import get_settings

from .client import ScalarsClientProtocol, ScalarsServiceClient


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
    def __init__(self, client: ScalarsClientProtocol | None = None):
        if client is None:
            settings = get_settings()
            client = ScalarsServiceClient(settings.scalars_service_url)
        self.client = client

    async def create_project_table(self, project_id: str) -> dict[str, Any]:
        return await self.client.create_project_table(project_id)

    async def log_scalar(
        self, project_id: str, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self.client.log_scalar(project_id, experiment_id, payload)

    async def log_scalars_batch(
        self, project_id: str, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self.client.log_scalars_batch(project_id, experiment_id, payload)

    async def get_scalars(
        self,
        project_id: str,
        experiment_ids: Iterable[str] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
    ) -> dict[str, Any]:
        return await self.client.get_scalars(
            project_id=project_id,
            experiment_ids=experiment_ids,
            max_points=max_points,
            return_tags=return_tags,
        )


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
