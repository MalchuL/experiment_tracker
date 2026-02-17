from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import httpx

from .config import SDKConfig, load_config
from .models import (
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentStatus,
    ExperimentUpdateRequest,
    LastLoggedExperimentsRequest,
    LastLoggedExperimentsResponse,
    MetricCreateRequest,
    ScalarLogRequest,
)
from .queue import RequestItem, RequestQueue
from .logger import logger


class _Unset:
    pass


Unset = _Unset()


def raise_for_status(response: httpx.Response) -> None:
    try:
        data = response.json()
    except json.JSONDecodeError:
        data = response.text
    logger.error(
        f"error_response: {data}",
        extra={"path": response.request.url, "error": data},
    )
    response.raise_for_status()


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
        self,
        project_id: str | UUID,
        name: str,
        description: str = "",
        color: Optional[str | Unset] = Unset,
        parent_experiment_id: Optional[str | UUID | Unset] = Unset,
        features: Optional[dict[str, Any] | Unset] = Unset,
        git_diff: Optional[str | Unset] = Unset,
        status: ExperimentStatus = ExperimentStatus.PLANNED,
    ) -> ExperimentResponse:
        """Create a new experiment for the given project.

        Args:
            project_id: Project UUID string.
            name: Experiment name.
            description: Optional description.

        Returns:
            ExperimentResponse with created experiment data.
        """

        kwargs: dict[str, Any] = {}
        if color is not Unset:
            kwargs["color"] = color
        if parent_experiment_id is not Unset:
            kwargs["parentExperimentId"] = parent_experiment_id
        if features is not Unset:
            kwargs["features"] = features
        if git_diff is not Unset:
            kwargs["gitDiff"] = git_diff
        payload = ExperimentCreateRequest(
            projectId=project_id,
            name=name,
            description=description,
            status=status,
            **kwargs,
        )
        response = self._client.post(
            "/api/experiments", json=payload.model_dump(exclude_unset=True)
        )
        raise_for_status(response)
        return ExperimentResponse.model_validate(response.json())

    def update_experiment(
        self,
        experiment_id: str | UUID,
        name: Optional[str | Unset] = Unset,
        description: Optional[str | Unset] = Unset,
        color: Optional[str | Unset] = Unset,
        parent_experiment_id: Optional[str | UUID | Unset] = Unset,
        features: Optional[dict[str, Any] | Unset] = Unset,
        git_diff: Optional[str | Unset] = Unset,
        status: Optional[ExperimentStatus | Unset] = Unset,
        progress: Optional[int | Unset] = Unset,
    ) -> ExperimentResponse:
        """Update an experiment.

        Args:
            experiment_id: Experiment UUID string.
            name: Optional experiment name.
            description: Optional description.
            color: Optional color.
            parent_experiment_id: Optional parent experiment UUID.
            features: Optional features.
            git_diff: Optional git diff.
            status: Optional status.
            progress: Optional progress.

        Returns:
            ExperimentResponse with updated experiment data.
        """
        kwargs: dict[str, Any] = {}
        if name is not Unset:
            kwargs["name"] = name
        if description is not Unset:
            kwargs["description"] = description
        if color is not Unset:
            kwargs["color"] = color
        if parent_experiment_id is not Unset:
            kwargs["parentExperimentId"] = parent_experiment_id
        if features is not Unset:
            kwargs["features"] = features
        if git_diff is not Unset:
            kwargs["gitDiff"] = git_diff
        if status is not Unset:
            kwargs["status"] = status
        if progress is not Unset:
            kwargs["progress"] = progress
        payload = ExperimentUpdateRequest(**kwargs)
        response = self._client.patch(
            f"/api/experiments/{experiment_id}",
            json=payload.model_dump(exclude_unset=True),
        )
        raise_for_status(response)
        return ExperimentResponse.model_validate(response.json())

    def get_experiment(self, experiment_id: str) -> ExperimentResponse:
        """Fetch an experiment by ID.

        Args:
            experiment_id: Experiment UUID string.

        Returns:
            ExperimentResponse with experiment data.
        """
        response = self._client.get(f"/api/experiments/{experiment_id}")
        raise_for_status(response)
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
        tags: list[str] | None = None,
    ) -> None:
        """Enqueue a scalar log request for the experiment.

        Args:
            experiment_id: Experiment UUID string.
            name: Scalar name.
            value: Scalar value.
            step: Training step or iteration.
            tags: Optional tags attached to the scalar point.
        """
        payload = ScalarLogRequest(scalars={name: value}, step=step, tags=tags)
        self._queue.enqueue(
            RequestItem(
                method="POST",
                path=f"/api/scalars/log/{experiment_id}",
                json=payload.model_dump(exclude_none=True),
            )
        )

    def log_scalars(
        self,
        experiment_id: str,
        scalars: dict[str, float],
        step: int = 0,
        tags: list[str] | None = None,
    ) -> None:
        """Enqueue a scalar log request with multiple scalar values.

        Args:
            experiment_id: Experiment UUID string.
            scalars: Scalar name/value pairs.
            step: Training step or iteration.
            tags: Optional tags attached to the scalar point.
        """
        payload = ScalarLogRequest(scalars=scalars, step=step, tags=tags)
        self._queue.enqueue(
            RequestItem(
                method="POST",
                path=f"/api/scalars/log/{experiment_id}",
                json=payload.model_dump(exclude_none=True),
            )
        )

    def get_scalars(
        self,
        experiment_id: str,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get scalar points for a single experiment.

        Args:
            experiment_id: Experiment UUID string.
            max_points: Maximum number of points to fetch.
            return_tags: Whether to include tags in the response.
            start_time: Optional inclusive lower bound for point timestamps.
            end_time: Optional inclusive upper bound for point timestamps.
        """
        params: dict[str, Any] = {"return_tags": return_tags}
        if max_points is not None:
            params["max_points"] = max_points
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()
        response = self._client.get(f"/api/scalars/get/{experiment_id}", params=params)
        raise_for_status(response)
        return response.json()

    def get_project_scalars(
        self,
        project_id: str,
        experiment_ids: list[str] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get scalar points for a project, optionally filtered by experiment IDs."""
        params: dict[str, Any] = {"return_tags": return_tags}
        if experiment_ids:
            params["experiment_id"] = experiment_ids
        if max_points is not None:
            params["max_points"] = max_points
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()
        response = self._client.get(
            f"/api/scalars/get/project/{project_id}", params=params
        )
        raise_for_status(response)
        return response.json()

    def get_last_logged_experiments(
        self, project_id: str, experiment_ids: list[str] | None = None
    ) -> LastLoggedExperimentsResponse:
        """Get last scalar logging timestamps for project experiments."""
        payload = LastLoggedExperimentsRequest(experiment_ids=experiment_ids)
        response = self._client.post(
            f"/api/scalars/last_logged/{project_id}",
            json=payload.model_dump(),
        )
        raise_for_status(response)
        return LastLoggedExperimentsResponse.model_validate(response.json())

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
