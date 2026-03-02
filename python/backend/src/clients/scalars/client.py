from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import msgpack

from .dto import (
    CreateProjectTableRequestDTO,
    CreateProjectTableResponseDTO,
    GetScalarsResponseDTO,
    LastLoggedExperimentsRequestDTO,
    LastLoggedExperimentsResponseDTO,
    LogScalarsBatchRequestDTO,
    LogScalarRequestDTO,
    LogScalarResponseDTO,
    ScalarsQueryDTO,
)


class ScalarsServiceClient:
    ENDPOINTS = {
        "create_project_table": "/projects",
        "log_scalar": lambda project_id, experiment_id: f"/scalars/log/{project_id}/{experiment_id}",
        "log_scalars_batch": lambda project_id, experiment_id: f"/scalars/log_batch/{project_id}/{experiment_id}",
        "get_scalars": lambda project_id: f"/scalars/get/{project_id}",
        "get_last_logged_experiments": lambda project_id: f"/scalars/last_logged/{project_id}",
    }

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_project_table(self, project_id: UUID) -> CreateProjectTableResponseDTO:
        payload = CreateProjectTableRequestDTO(project_id=project_id)
        response = await self._request(
            "POST",
            self.ENDPOINTS["create_project_table"],
            json_payload=payload.model_dump(mode="json"),
            use_msgpack=False,
        )
        return CreateProjectTableResponseDTO.model_validate(response)

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO:
        response = await self._request(
            "POST",
            self.ENDPOINTS["log_scalar"](project_id, experiment_id),
            json_payload=payload.model_dump(mode="json"),
            use_msgpack=False,
        )
        return LogScalarResponseDTO.model_validate(response)

    async def log_scalars_batch(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO:
        response = await self._request(
            "POST",
            self.ENDPOINTS["log_scalars_batch"](project_id, experiment_id),
            json_payload=payload.model_dump(mode="json"),
            use_msgpack=False,
        )
        return LogScalarResponseDTO.model_validate(response)

    async def get_scalars(self, query: ScalarsQueryDTO) -> GetScalarsResponseDTO:
        response = await self._request(
            "GET",
            self.ENDPOINTS["get_scalars"](query.project_id),
            params=query.as_query_params(),
            accept_msgpack=False,
        )
        return GetScalarsResponseDTO.model_validate(response)

    async def get_last_logged_experiments(
        self, project_id: UUID, payload: LastLoggedExperimentsRequestDTO
    ) -> LastLoggedExperimentsResponseDTO:
        response = await self._request(
            "POST",
            self.ENDPOINTS["get_last_logged_experiments"](project_id),
            json_payload=payload.model_dump(mode="json"),
            use_msgpack=False,
        )
        return LastLoggedExperimentsResponseDTO.model_validate(response)

    async def _request(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        use_msgpack: bool = False,
        accept_msgpack: bool = False,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {}
        content = None
        if use_msgpack and json_payload is not None:
            content = msgpack.packb(json_payload, use_bin_type=True)
            headers["Content-Type"] = "application/msgpack"
        if accept_msgpack:
            headers["Accept"] = "application/msgpack"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                content=content,
                json=None if content is not None else json_payload,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if content_type.startswith("application/msgpack"):
                return msgpack.unpackb(response.content, raw=False)
            return response.json()


class NoOpScalarsServiceClient(ScalarsServiceClient):
    def __init__(self) -> None:
        super().__init__(base_url="http://noop")

    async def create_project_table(self, project_id: UUID) -> CreateProjectTableResponseDTO:
        return CreateProjectTableResponseDTO(status="noop")

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO:
        return LogScalarResponseDTO(status="logged")

    async def log_scalars_batch(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO:
        return LogScalarResponseDTO(status="logged")

    async def get_scalars(self, query: ScalarsQueryDTO) -> GetScalarsResponseDTO:
        return GetScalarsResponseDTO(data=[])

    async def get_last_logged_experiments(
        self, project_id: UUID, payload: LastLoggedExperimentsRequestDTO
    ) -> LastLoggedExperimentsResponseDTO:
        return LastLoggedExperimentsResponseDTO(data=[])

