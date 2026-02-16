from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Protocol
from uuid import UUID

import httpx
import msgpack


class ScalarsServiceClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_project_table(self, project_id: UUID) -> dict[str, Any]:
        payload = {"project_id": str(project_id)}
        return await self._request(
            "POST",
            "/projects",
            json_payload=payload,
            use_msgpack=False,
        )

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/scalars/log/{project_id}/{experiment_id}",
            json_payload=payload,
            use_msgpack=False,
        )

    async def log_scalars_batch(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/scalars/log_batch/{project_id}/{experiment_id}",
            json_payload=payload,
            use_msgpack=False,
        )

    async def get_scalars(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"return_tags": return_tags}
        if experiment_ids:
            params["experiment_id"] = [str(experiment_id) for experiment_id in experiment_ids]
        if max_points is not None:
            params["max_points"] = max_points
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()
        return await self._request(
            "GET",
            f"/scalars/get/{project_id}",
            params=params,
            accept_msgpack=False,
        )

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


class ScalarsClientProtocol(Protocol):
    async def create_project_table(self, project_id: UUID) -> dict[str, Any]: ...

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def log_scalars_batch(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def get_scalars(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]: ...


class NoOpScalarsServiceClient(ScalarsServiceClient):
    def __init__(self) -> None:
        super().__init__(base_url="http://noop")

    async def create_project_table(self, project_id: UUID) -> dict[str, Any]:
        return {}

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def log_scalars_batch(
        self, project_id: UUID, experiment_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    async def get_scalars(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        return {}
