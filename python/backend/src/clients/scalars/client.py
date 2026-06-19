"""HTTP client for the **scalars** satellite (ClickHouse time series, artifacts metadata, admin).

Most routes live under ``/scalars`` (log, query). Project-scoped operations that touch
**multiple** ClickHouse tables (scalars runs, ``artifacts_info``, ``last_logged``), usage
aggregates, and admin table listing are exposed by the satellite on ``/projects`` — this
client keeps the URL map in ``ENDPOINTS`` so the main API stays aligned with routing
changes in ``python/scalars_service``.
"""

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
    ScalarsCompactColumnsResponseDTO,
    ScalarsDeleteExperimentDataResponseDTO,
    ScalarsDeleteProjectTablesResponseDTO,
    ScalarsDropStorageTableResponseDTO,
    ScalarsExperimentUsageResponseDTO,
    ScalarsListStorageTablesResponseDTO,
    ScalarsProjectUsageResponseDTO,
    ScalarsQueryDTO,
    ScalarNamesResponseDTO,
)


class ScalarsServiceClient:
    """Async JSON/msgpack client; mirrors the scalars FastAPI app paths used by the backend."""

    ENDPOINTS = {
        "create_project_table": "/projects",
        "log_scalar": lambda project_id, experiment_id: f"/scalars/log/{project_id}/{experiment_id}",
        "log_scalars_batch": lambda project_id, experiment_id: f"/scalars/log_batch/{project_id}/{experiment_id}",
        "get_scalars": lambda project_id: f"/scalars/get/{project_id}",
        "get_scalar_names": lambda project_id: f"/scalars/names/{project_id}",
        "get_last_logged_experiments": lambda project_id: f"/last_logged/{project_id}",
        "delete_experiment": lambda project_id, experiment_id: f"/projects/{project_id}/experiments/{experiment_id}",
        "delete_project": lambda project_id: f"/projects/{project_id}",
        "compact_project": lambda project_id: f"/scalars/projects/{project_id}/compact-columns",
        "project_usage": lambda project_id: f"/projects/{project_id}/usage",
        "experiment_usage": lambda project_id, experiment_id: f"/projects/{project_id}/experiments/{experiment_id}/usage",
        "list_storage_tables": "/projects/admin/storage/tables",
        "drop_storage_table": lambda table_name: f"/projects/admin/storage/tables/{table_name}",
    }

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO:
        payload = CreateProjectTableRequestDTO(project_id=project_id)
        raw = await self._request(
            "POST",
            self.ENDPOINTS["create_project_table"],
            json_payload=payload.model_dump(mode="json", by_alias=True),
            use_msgpack=False,
        )
        return CreateProjectTableResponseDTO.model_validate(raw)

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

    async def get_scalar_names(self, project_id: UUID) -> ScalarNamesResponseDTO:
        response = await self._request(
            "GET",
            self.ENDPOINTS["get_scalar_names"](project_id),
            accept_msgpack=False,
        )
        return ScalarNamesResponseDTO.model_validate(response)

    async def get_last_logged_experiments(
        self,
        project_id: UUID,
        payload: LastLoggedExperimentsRequestDTO,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> LastLoggedExperimentsResponseDTO:
        params: dict[str, Any] | None = None
        if limit is not None or offset is not None:
            params = {}
            if limit is not None:
                params["limit"] = limit
            if offset is not None:
                params["offset"] = offset
        response = await self._request(
            "POST",
            self.ENDPOINTS["get_last_logged_experiments"](project_id),
            json_payload=payload.model_dump(mode="json"),
            params=params,
            use_msgpack=False,
        )
        return LastLoggedExperimentsResponseDTO.model_validate(response)

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO:
        """Remove all ClickHouse rows for one experiment across managed project tables.

        The scalars service orchestrates deletes on the scalars table, ``artifacts_info``,
        ``last_logged``, compacts orphaned metric columns, and invalidates caches. Used
        when an experiment is deleted from Postgres or during bulk admin cleanup.
        """
        raw = await self._request(
            "DELETE",
            self.ENDPOINTS["delete_experiment"](project_id, experiment_id),
            use_msgpack=False,
        )
        return ScalarsDeleteExperimentDataResponseDTO.model_validate(raw)

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO:
        """Drop ClickHouse tables owned by a project (scalars + related per-project tables)."""
        raw = await self._request(
            "DELETE", self.ENDPOINTS["delete_project"](project_id), use_msgpack=False
        )
        return ScalarsDeleteProjectTablesResponseDTO.model_validate(raw)

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO:
        """Ask the satellite to drop unused physical metric columns after mapping cleanup."""
        raw = await self._request(
            "POST", self.ENDPOINTS["compact_project"](project_id), use_msgpack=False
        )
        return ScalarsCompactColumnsResponseDTO.model_validate(raw)

    async def get_project_usage(self, project_id: UUID) -> ScalarsProjectUsageResponseDTO:
        """Aggregate ClickHouse disk usage for all managed tables belonging to ``project_id``.

        Used by the main API's project usage endpoint together with object-storage totals.
        """
        raw = await self._request(
            "GET", self.ENDPOINTS["project_usage"](project_id), use_msgpack=False
        )
        return ScalarsProjectUsageResponseDTO.model_validate(raw)

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO:
        """Return row counts / bytes attributed to a single experiment in ClickHouse.

        Complements ``get_experiment_usage`` on object storage for the combined experiment
        usage DTO shown in the UI danger zone.
        """
        raw = await self._request(
            "GET",
            self.ENDPOINTS["experiment_usage"](project_id, experiment_id),
            use_msgpack=False,
        )
        return ScalarsExperimentUsageResponseDTO.model_validate(raw)

    async def list_storage_tables(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ScalarsListStorageTablesResponseDTO:
        """Paginated admin listing of ``scalars_*`` / ``artifacts_info_*`` tables in ClickHouse.

        Requires the admin panel flow on the main API to pass ``X-Admin-Key``; the HTTP
        call here is unauthenticated at the client layer (service URL is internal).
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if q is not None and q.strip():
            params["q"] = q.strip()
        raw = await self._request(
            "GET", self.ENDPOINTS["list_storage_tables"], use_msgpack=False, params=params
        )
        return ScalarsListStorageTablesResponseDTO.model_validate(raw)

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO:
        """Destructive admin op: ``DROP TABLE`` for a managed scalars-related table name."""
        raw = await self._request(
            "DELETE",
            self.ENDPOINTS["drop_storage_table"](table_name),
            use_msgpack=False,
        )
        return ScalarsDropStorageTableResponseDTO.model_validate(raw)

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
    """Test/diagnostics stand-in: never performs HTTP; returns success-shaped DTOs."""

    def __init__(self) -> None:
        super().__init__(base_url="http://noop")

    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO:
        return CreateProjectTableResponseDTO(table_name="", project_id=project_id)

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO:
        return LogScalarResponseDTO(status="logged")

    async def log_scalars_batch(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO:
        return LogScalarResponseDTO(status="logged")

    async def get_scalars(self, query: ScalarsQueryDTO) -> GetScalarsResponseDTO:
        _ = query
        return GetScalarsResponseDTO(data=[], has_next=False, size=0, total=0)

    async def get_scalar_names(self, project_id: UUID) -> ScalarNamesResponseDTO:
        _ = project_id
        return ScalarNamesResponseDTO(scalar_names=[])

    async def get_last_logged_experiments(
        self,
        project_id: UUID,
        payload: LastLoggedExperimentsRequestDTO,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> LastLoggedExperimentsResponseDTO:
        _ = (project_id, payload, limit, offset)
        return LastLoggedExperimentsResponseDTO(data=[], has_next=False, size=0, total=0)

    async def delete_experiment_data(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsDeleteExperimentDataResponseDTO:
        _ = (project_id, experiment_id)
        return ScalarsDeleteExperimentDataResponseDTO(deleted=True)

    async def delete_project_table(
        self, project_id: UUID
    ) -> ScalarsDeleteProjectTablesResponseDTO:
        _ = project_id
        return ScalarsDeleteProjectTablesResponseDTO(message="noop")

    async def compact_project_columns(
        self, project_id: UUID
    ) -> ScalarsCompactColumnsResponseDTO:
        _ = project_id
        return ScalarsCompactColumnsResponseDTO(dropped_columns=[])

    async def get_project_usage(self, project_id: UUID) -> ScalarsProjectUsageResponseDTO:
        return ScalarsProjectUsageResponseDTO(
            project_id=project_id, total_bytes=0, tables=[]
        )

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ScalarsExperimentUsageResponseDTO:
        return ScalarsExperimentUsageResponseDTO(
            project_id=project_id,
            experiment_id=experiment_id,
            bytes=0,
            rows=0,
        )

    async def list_storage_tables(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ScalarsListStorageTablesResponseDTO:
        _ = (q, limit, offset)
        return ScalarsListStorageTablesResponseDTO(
            tables=[], total=0, limit=limit, offset=offset
        )

    async def drop_storage_table(
        self, table_name: str
    ) -> ScalarsDropStorageTableResponseDTO:
        return ScalarsDropStorageTableResponseDTO(dropped=True, table=table_name)
