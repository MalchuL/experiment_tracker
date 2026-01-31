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
        """Initialize a synchronous SDK client for Experiment Tracker.

        Args:
            base_url: Backend base URL, e.g. "http://127.0.0.1:8000".
            api_token: API token used for Authorization header.
            timeout: HTTP timeout (seconds) for requests.
            max_queue_size: Max queued metric requests before blocking.

        Example:
            client = ExperimentClient(
                base_url="http://127.0.0.1:8000",
                api_token="my-token",
            )
        """
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
        """Create a client using config saved by the CLI.

        Returns:
            ExperimentClient instance.

        Raises:
            RuntimeError: If config has not been initialized.

        Example:
            client = ExperimentClient.from_config()
        """
        config = load_config()
        if config is None:
            raise RuntimeError("SDK config not found. Run `experiment-tracker init`.")
        return cls(base_url=config.base_url, api_token=config.api_token)

    def create_experiment(
        self, project_id: str, name: str, description: str = ""
    ) -> ExperimentResponse:
        """Create a new experiment for the given project.

        Args:
            project_id: Project UUID string.
            name: Experiment name.
            description: Optional description.

        Returns:
            ExperimentResponse with created experiment data.
        """
        payload = ExperimentCreateRequest(
            projectId=project_id, name=name, description=description
        )
        response = self._client.post("/api/experiments", json=payload.model_dump())
        response.raise_for_status()
        return ExperimentResponse.model_validate(response.json())

    def get_experiment(self, experiment_id: str) -> ExperimentResponse:
        """Fetch an experiment by ID.

        Args:
            experiment_id: Experiment UUID string.

        Returns:
            ExperimentResponse with experiment data.
        """
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
        """Enqueue a metric log request for the experiment.

        Args:
            experiment_id: Experiment UUID string.
            name: Metric name.
            value: Metric value.
            step: Training step or iteration.
            direction: "maximize" or "minimize".

        Example:
            client.log_metric(exp.id, name="accuracy", value=0.91, step=10)
        """
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
        """Alias for log_metric with default direction.

        Args:
            experiment_id: Experiment UUID string.
            name: Metric name.
            value: Metric value.
            step: Training step or iteration.
        """
        self.log_metric(experiment_id, name, value, step=step)

    def log_artifact(self, experiment_id: str, name: str, path: str) -> None:
        """Emit a warning because artifacts are not supported yet.

        Args:
            experiment_id: Experiment UUID string.
            name: Artifact name.
            path: Local path to artifact.
        """
        logger.warning(
            "artifact_logging_not_supported",
            extra={"experiment_id": experiment_id, "name": name, "path": path},
        )

    def flush(self) -> None:
        """Block until queued requests are sent.

        Use this before exiting to ensure metrics are delivered.
        """
        self._queue.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        self._queue.close()
        self._client.close()
