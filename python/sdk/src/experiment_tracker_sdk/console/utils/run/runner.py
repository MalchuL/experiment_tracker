from __future__ import annotations

from experiment_tracker_sdk import ExpTracker, ExperimentStatus
from experiment_tracker_sdk.client import APIRequestsRegistry, ExperimentTrackerClient
from experiment_tracker_sdk.client.api_access import resolve_client_and_registry
from experiment_tracker_sdk.logger import logger
from experiment_tracker_sdk.utils.color_utils import random_hex_color
from experiment_tracker_sdk.utils.experiment_init_strategy import (
    InitParams,
    MultipleItemsResolveStrategy,
    MultipleResolvingContextObject,
    ExperimentInitStrategy,
)


class RunSample:
    """Console helper that initializes an ``ExpTracker`` for a run command."""

    def __init__(
        self,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> None:
        resolved = resolve_client_and_registry(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )
        self.exp_tracker: ExpTracker | None = None
        self._request_client = resolved.request_client
        self._api_requests_registry = resolved.api_requests_registry
        self._init_strategy = ExperimentInitStrategy(
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )
        self._logger = logger.getChild("runner")

    def init(
        self,
        experiment_name_or_id: str,
        project_name_or_id: str | None = None,
        team_name_or_id: str | None = None,
        init_params: InitParams = InitParams(),
    ) -> None:
        """Initialize the run sample tracker.

        Args:
            experiment_name_or_id: Experiment name or ID to resolve.
            project_name_or_id: Project name or ID to resolve.
            team_name_or_id: Optional team name or ID used for resolution and
                creation.
            init_params: Creation and ambiguity-resolution options.
        """
        result = self._init_strategy.init(
            experiment_name_or_id=experiment_name_or_id,
            project_name_or_id=project_name_or_id,
            team_name_or_id=team_name_or_id,
            init_params=init_params,
        )
        self.exp_tracker = ExpTracker(
            result.experiment.id,
            result.project.id,
            self._api_requests_registry,
            self._request_client,
            experiment_instance=result.experiment,
        )
        with self.exp_tracker:
            self.exp_tracker.color(random_hex_color())

    def mark_completed(self) -> None:
        """Mark the initialized run tracker as completed."""
        if self.exp_tracker is None:
            return
        with self.exp_tracker:
            self.exp_tracker.progress(100)
            self.exp_tracker.status(ExperimentStatus.COMPLETE)

    def mark_failed(self) -> None:
        """Mark the initialized run tracker as failed."""
        if self.exp_tracker is None:
            return
        with self.exp_tracker:
            self.exp_tracker.status(ExperimentStatus.FAILED)


__all__ = [
    "RunSample",
    "InitParams",
    "MultipleItemsResolveStrategy",
    "MultipleResolvingContextObject",
]
