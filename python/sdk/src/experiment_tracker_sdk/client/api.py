from experiment_tracker_sdk.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.request import ApiRequestSpec
from experiment_tracker_sdk.client.domain import (
    ExperimentRequestSpecFactory,
    MetricRequestSpecFactory,
    ProjectRequestSpecFactory,
    ScalarsRequestSpecFactory,
    HypothesisRequestSpecFactory,
    TeamRequestSpecFactory,
)
from pydantic import BaseModel
from typing import Any, TypeVar

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class API:
    def __init__(self, client: ExperimentTrackerClient):
        self._client = client
        self._experiment_service = ExperimentRequestSpecFactory()
        self._metric_service = MetricRequestSpecFactory()
        self._project_service = ProjectRequestSpecFactory()
        self._scalars_service = ScalarsRequestSpecFactory()
        self._hypothesis_service = HypothesisRequestSpecFactory()
        self._team_service = TeamRequestSpecFactory()

    @property
    def experiments(self) -> ExperimentRequestSpecFactory:
        return self._experiment_service

    @property
    def metrics(self) -> MetricRequestSpecFactory:
        return self._metric_service

    @property
    def projects(self) -> ProjectRequestSpecFactory:
        return self._project_service

    @property
    def scalars(self) -> ScalarsRequestSpecFactory:
        return self._scalars_service

    @property
    def hypotheses(self) -> HypothesisRequestSpecFactory:
        return self._hypothesis_service

    @property
    def teams(self) -> TeamRequestSpecFactory:
        return self._team_service

    def request(
        self, request_spec: ApiRequestSpec[ResponseT]
    ) -> ResponseT | list[ResponseT] | dict[str, Any]:
        return self._client.request(request_spec)

    def queued_request(self, request_spec: ApiRequestSpec[Any]) -> None:
        self._client.queued_request(request_spec)

    def flush(self) -> None:
        """Flush the request queue."""
        self._client.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        self._client.close()
