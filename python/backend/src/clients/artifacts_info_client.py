"""HTTP client for scalars_service artifacts_info API."""

from __future__ import annotations

from typing import Any, Iterable, Protocol
from uuid import UUID

import httpx


class ArtifactsInfoClientProtocol(Protocol):
    """Protocol for scalars_service artifacts_info API."""

    async def log_artifact(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def get_artifacts(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        artifact_types: Iterable[str] | None = None,
        artifact_names: Iterable[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]: ...


class ArtifactsInfoClient:
    """HTTP client for scalars_service artifacts_info API."""

    ENDPOINTS = {
        "log_artifact": lambda project_id, experiment_id: f"/artifacts_info/log/{project_id}/{experiment_id}",
        "get_artifacts": lambda project_id: f"/artifacts_info/get/{project_id}",
    }

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def log_artifact(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{self.ENDPOINTS['log_artifact'](project_id, experiment_id)}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def get_artifacts(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        artifact_types: Iterable[str] | None = None,
        artifact_names: Iterable[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if experiment_ids:
            params["experiment_id"] = [str(e) for e in experiment_ids]
        if artifact_types:
            params["artifact_type"] = list(artifact_types)
        if artifact_names:
            params["artifact_name"] = list(artifact_names)
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}{self.ENDPOINTS['get_artifacts'](project_id)}",
                params=params,
            )
            response.raise_for_status()
            return response.json()
