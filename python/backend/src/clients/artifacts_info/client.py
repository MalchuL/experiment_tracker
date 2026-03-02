"""HTTP client for scalars_service artifacts_info API."""

from __future__ import annotations

from typing import Any
from typing import Iterable
from uuid import UUID

import httpx

from .dto import ArtifactsInfoResultDTO, LogArtifactRequestDTO, LogArtifactResponseDTO


class ArtifactsInfoClient:
    ENDPOINTS = {
        "log_artifact": lambda project_id, experiment_id: f"/artifacts_info/log/{project_id}/{experiment_id}",
        "get_artifacts": lambda project_id: f"/artifacts_info/get/{project_id}",
    }

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def log_artifact(
        self, project_id: UUID, experiment_id: UUID, payload: LogArtifactRequestDTO
    ) -> LogArtifactResponseDTO:
        response = await self._request(
            "POST",
            self.ENDPOINTS["log_artifact"](project_id, experiment_id),
            json_payload=payload.model_dump(mode="json"),
        )
        return LogArtifactResponseDTO.model_validate(response)

    async def get_artifacts(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        artifact_types: Iterable[str] | None = None,
        artifact_names: Iterable[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        params: dict[str, object] = {}
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
        response = await self._request(
            "GET",
            self.ENDPOINTS["get_artifacts"](project_id),
            params=params,
        )
        return ArtifactsInfoResultDTO.model_validate(response)

    async def _request(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                json=json_payload,
                params=params,
            )
            response.raise_for_status()
            return response.json()

