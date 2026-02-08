from __future__ import annotations

from typing import Any, Iterable

import httpx
import msgpack


class ScalarsServiceClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_project_table(self, project_id: str) -> dict[str, Any]:
        payload = {"project_id": project_id}
        return await self._request(
            "POST",
            "/projects",
            json_payload=payload,
            use_msgpack=False,
        )

    async def log_scalar(
        self, project_id: str, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/scalars/log/{project_id}/{experiment_id}",
            json_payload=payload,
            use_msgpack=False,
        )

    async def log_scalars_batch(
        self, project_id: str, experiment_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/scalars/log_batch/{project_id}/{experiment_id}",
            json_payload=payload,
            use_msgpack=False,
        )

    async def get_scalars(
        self,
        project_id: str,
        experiment_ids: Iterable[str] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"return_tags": return_tags}
        if experiment_ids:
            params["experiment_id"] = list(experiment_ids)
        if max_points is not None:
            params["max_points"] = max_points
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
