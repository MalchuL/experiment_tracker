from __future__ import annotations

import logging
from typing import Optional

import httpx

from .config import SDKConfig, load_config
from .models import ExperimentCreateRequest, ExperimentResponse, MetricCreateRequest
from .queue import RequestItem, RequestQueue

logger = logging.getLogger("experiment_tracker_sdk")


class ExperimentClient:
    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = 10.0,
        max_queue_size: int = 1000,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_token}"},
        )
        self._queue = RequestQueue(self._client, max_queue_size=max_queue_size)

    @classmethod
    def from_config(cls) -> "ExperimentClient":
        config = load_config()
        if config is None:
            raise RuntimeError("SDK config not found. Run `experiment-tracker init`.")
        return cls(base_url=config.base_url, api_token=config.api_token)

    def create_experiment(
        self, project_id: str, name: str, description: str = ""
    ) -> ExperimentResponse:
        payload = ExperimentCreateRequest(
            projectId=project_id, name=name, description=description
        )
        response = self._client.post("/api/experiments", json=payload.model_dump())
        response.raise_for_status()
        return ExperimentResponse.model_validate(response.json())

    def get_experiment(self, experiment_id: str) -> ExperimentResponse:
        response = self._client.get(f"/api/experiments/{experiment_id}")
        response.raise_for_status()
        return ExperimentResponse.model_validate(response.json())

    def log_metric(
        self,
        experiment_id: str,
        name: str,
        value: float,
        step: int = 0,
        direction: str = "maximize",
    ) -> None:
        payload = MetricCreateRequest(
            experimentId=experiment_id,
            name=name,
            value=value,
            step=step,
            direction=direction,
        )
        self._queue.enqueue(
            RequestItem(method="POST", path="/api/metrics", json=payload.model_dump())
        )

    def log_scalar(
        self,
        experiment_id: str,
        name: str,
        value: float,
        step: int = 0,
    ) -> None:
        self.log_metric(experiment_id, name, value, step=step)

    def log_artifact(self, experiment_id: str, name: str, path: str) -> None:
        logger.warning(
            "artifact_logging_not_supported",
            extra={"experiment_id": experiment_id, "name": name, "path": path},
        )

    def flush(self) -> None:
        self._queue.flush()

    def close(self) -> None:
        self._queue.close()
        self._client.close()
