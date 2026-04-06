"""HTTP client for scalars_service artifacts_info API."""

from __future__ import annotations

from typing import Any
from typing import Iterable
from uuid import UUID

import httpx

from .dto import (
    ArtifactType,
    ArtifactsInfoResultDTO,
    LogArtifactRequestDTO,
    LogArtifactResponseDTO,
)

QueryParamScalar = str | int | float | bool | None
QueryParamValue = QueryParamScalar | list[QueryParamScalar]


class ArtifactsInfoClient:
    """HTTP client for scalars_service artifacts_info API.

    This client is used to log and get artifacts info from the scalars_service.
    Usefull to store artifacts that depends on the experiment and step.

    Args:
        base_url: The base URL of the scalars_service.
        timeout: The timeout for the HTTP requests.

    Attributes:
        base_url: The base URL of the scalars_service.
        timeout: The timeout for the HTTP requests.
    """

    ENDPOINTS: dict[str, Any] = {
        "log_artifact_at_step": lambda project_id, experiment_id: f"/artifacts_info/log/{project_id}/{experiment_id}",
        "get_artifacts": lambda project_id: f"/artifacts_info/get/{project_id}",
    }

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def log_artifact_at_step(
        self, project_id: UUID, experiment_id: UUID, payload: LogArtifactRequestDTO
    ) -> LogArtifactResponseDTO:
        """Log an artifact info to the scalars_service.

        Args:
            project_id: The ID of the project.
            experiment_id: The ID of the experiment (that under project).
            payload: The payload to log.

        Returns:
            The response from the scalars_service.
        """
        response = await self._request(
            "POST",
            self.ENDPOINTS["log_artifact_at_step"](project_id, experiment_id),
            json_payload=payload.model_dump(mode="json"),
        )
        return LogArtifactResponseDTO.model_validate(response)

    async def get_artifacts(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        artifact_types: Iterable[ArtifactType] | None = None,
        artifact_names: Iterable[str] | None = None,
        steps: Iterable[int] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        """Get artifacts info from the scalars_service.

        Args:
            project_id: The ID of the project.
            experiment_ids: The IDs of the experiments (that under project).
            artifact_types: The types of the artifacts.
            artifact_names: The names of the artifacts.
            steps: Training step indices to filter by.
            start_time: The start time of the artifacts.
            end_time: The end time of the artifacts.

        Returns:
            ArtifactsInfoResultDTO: The response from the scalars_service.
        """
        params: dict[str, QueryParamValue] = {}
        if experiment_ids:
            params["experiment_id"] = [str(e) for e in experiment_ids]
        if artifact_types:
            params["artifact_type"] = list(artifact_types)
        if artifact_names:
            params["artifact_name"] = list(artifact_names)
        if steps:
            params["step"] = list(steps)
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
        params: dict[str, QueryParamValue] | None = None,
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
