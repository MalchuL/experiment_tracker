"""Read experiments, hparams, and aggregated metrics from the main backend."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from mltools.config.settings import Settings, get_settings
from mltools.domain.hparam_importance.dto import TargetMetricDTO


class BackendClient:
    """Read experiments, hparams, and aggregated metric targets from the backend."""

    def __init__(self, settings: Settings | None = None, timeout: float = 30.0):
        """Initialize the backend HTTP adapter.

        Args:
            settings: Optional process settings; cached environment settings are used
                when omitted.
            timeout: Per-request HTTP timeout in seconds.

        Result:
            BackendClient configured with the backend base URL and scoped PAT.
        """
        self.settings = settings or get_settings()
        self.base_url = self.settings.backend_base_url.rstrip("/")
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        """Build authentication headers for backend requests.

        Returns:
            dict[str, str]: Bearer authorization header containing the configured PAT.
        """
        return {"Authorization": f"Bearer {self.settings.backend_api_token}"}

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        """Execute one authenticated backend request and decode its JSON object.

        Args:
            method: HTTP method such as ``GET``.
            path: Backend-relative path including the ``/api`` prefix.
            **kwargs: Additional keyword arguments forwarded to ``httpx``.

        Returns:
            dict[str, Any]: Decoded JSON response object.

        Raises:
            httpx.HTTPStatusError: If the backend returns a non-success response.
            httpx.RequestError: If the backend cannot be reached.
        """
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.request(method, f"{self.base_url}{path}", **kwargs)
            response.raise_for_status()
            return response.json()

    async def list_experiments(self, project_id: UUID) -> list[dict[str, Any]]:
        """Fetch every experiment in a project across backend pagination.

        Args:
            project_id: Project whose experiments form the analysis population.

        Returns:
            list[dict[str, Any]]: Backend experiment payloads ordered by backend
            pagination.
        """
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = await self._request(
                "GET",
                f"/api/projects/{project_id}/experiments",
                params={"limit": 100, "offset": offset, "includeFeatures": "false"},
            )
            rows.extend(page["data"])
            if not page.get("hasNext"):
                return rows
            offset += len(page["data"])

    async def get_hparams(self, experiment_id: UUID) -> dict[str, Any] | None:
        """Fetch the current hyperparameter document for one experiment.

        Args:
            experiment_id: Experiment whose current hparams are requested.

        Returns:
            dict[str, Any] | None: Nested hparams object, or ``None`` when absent.
        """
        response = await self._request("GET", f"/api/experiments/{experiment_id}/hparams")
        return response.get("hparams")

    async def get_aggregated_metrics(
        self, project_id: UUID, targets: list[TargetMetricDTO]
    ) -> dict[tuple[str, str | None], dict[UUID, float]]:
        """Fetch configured aggregate values for selected target metrics.

        Args:
            project_id: Project that owns the tracked metric configuration.
            targets: Exact metric name/label keys selected for analysis.

        Returns:
            dict[tuple[str, str | None], dict[UUID, float]]: Mapping from each target
            metric key to experiment identifiers and their aggregate values.
        """
        requested = {(item.name, item.label) for item in targets}
        values: dict[tuple[str, str | None], dict[UUID, float]] = {
            key: {} for key in requested
        }
        offset = 0
        while True:
            page = await self._request(
                "GET",
                f"/api/projects/{project_id}/metrics",
                params={"limit": 100, "offset": offset},
            )
            for row in page["data"]:
                key = (row["name"], row.get("label"))
                if key in requested:
                    values[key][UUID(row["experimentId"])] = float(row["value"])
            if not page.get("hasNext"):
                return values
            offset += len(page["data"])
"""Authenticated HTTP adapter for reading analysis inputs from the main backend."""
