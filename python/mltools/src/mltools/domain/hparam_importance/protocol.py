"""Define infrastructure ports required by the hparam-importance domain."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from .dto import TargetMetricDTO


class BackendDataClientProtocol(Protocol):
    """Port for reading experiments, hparams, and metrics from the main backend."""

    async def list_experiments(self, project_id: UUID) -> list[dict[str, Any]]:
        """List every experiment available for analysis in a project.

        Args:
            project_id: Project whose experiments should be paged and returned.

        Returns:
            Experiment summaries containing at least identifiers and names.
        """
        ...

    async def get_hparams(self, experiment_id: UUID) -> dict[str, Any] | None:
        """Fetch the current hyperparameter document for an experiment.

        Args:
            experiment_id: Experiment whose current hparams are requested.

        Returns:
            Top-level hyperparameter object, or ``None`` when no document exists.
        """
        ...

    async def get_aggregated_metrics(
        self, project_id: UUID, targets: list[TargetMetricDTO]
    ) -> dict[tuple[str, str | None], dict[UUID, float]]:
        """Fetch configured aggregate values for requested target metrics.

        Args:
            project_id: Project containing the metric rows.
            targets: Structured metric name and optional label keys to retrieve.

        Returns:
            Mapping from each metric key to experiment identifiers and values.
        """
        ...


class ModelStorageProtocol(Protocol):
    """Port for persisting serialized trained-model artifacts."""

    def upload(self, key: str, content: bytes) -> None:
        """Upload a serialized artifact under a normalized object key.

        Args:
            key: Bucket-relative key used to store the artifact.
            content: Serialized model and preprocessing payload.

        Returns:
            None after the object is durably uploaded.
        """
        ...


class JobDispatcherProtocol(Protocol):
    """Port for dispatching a persisted job to asynchronous execution."""

    def dispatch(self, job_id: UUID) -> None:
        """Enqueue a previously persisted importance job.

        Args:
            job_id: Identifier of the pending job to execute.

        Returns:
            None after the job has been submitted to the task queue.
        """
        ...
"""Ports implemented by infrastructure adapters used by importance analysis."""
