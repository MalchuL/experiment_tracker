from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Protocol
from uuid import UUID

import httpx


class ObjectsServiceClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def log_object(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/objects/log/{project_id}/{experiment_id}",
            json_payload=payload,
        )

    async def log_objects_batch(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/objects/log_batch/{project_id}/{experiment_id}",
            json_payload=payload,
        )

    async def get_objects(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        object_types: Iterable[str] | None = None,
        names: Iterable[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if experiment_ids:
            params["experiment_id"] = [str(experiment_id) for experiment_id in experiment_ids]
        if object_types:
            params["object_type"] = list(object_types)
        if names:
            params["name"] = list(names)
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()
        return await self._request("GET", f"/objects/get/{project_id}", params=params)

    async def _request(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json_payload,
            )
            response.raise_for_status()
            return response.json()


class ObjectsClientProtocol(Protocol):
    async def log_object(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def log_objects_batch(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def get_objects(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        object_types: Iterable[str] | None = None,
        names: Iterable[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]: ...


class NoOpObjectsServiceClient(ObjectsServiceClient):
    def __init__(self) -> None:
        super().__init__(base_url="http://noop")

    async def log_object(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def log_objects_batch(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def get_objects(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        object_types: Iterable[str] | None = None,
        names: Iterable[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        return {"data": []}
