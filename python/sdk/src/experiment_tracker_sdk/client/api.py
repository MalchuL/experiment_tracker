from experiment_tracker_sdk.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.request import RequestSpec
from experiment_tracker_sdk.client.domain import (
    ExperimentService,
    MetricService,
    ProjectService,
    ScalarsService,
    HypothesisService,
    TeamService,
)
from pydantic import BaseModel
from typing import Any, TypeVar

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class API:
    def __init__(self, client: ExperimentTrackerClient):
        self._client = client
        self._experiment_service = ExperimentService()
        self._metric_service = MetricService()
        self._project_service = ProjectService()
        self._scalars_service = ScalarsService()
        self._hypothesis_service = HypothesisService()
        self._team_service = TeamService()

    @property
    def experiments(self) -> ExperimentService:
        return self._experiment_service

    @property
    def metrics(self) -> MetricService:
        return self._metric_service

    @property
    def projects(self) -> ProjectService:
        return self._project_service

    @property
    def scalars(self) -> ScalarsService:
        return self._scalars_service

    @property
    def hypotheses(self) -> HypothesisService:
        return self._hypothesis_service

    @property
    def teams(self) -> TeamService:
        return self._team_service

    def request(
        self, request: RequestSpec[ResponseT]
    ) -> ResponseT | list[ResponseT] | dict[str, Any]:
        return self._client.request(request)

    def queued_request(self, request: RequestSpec[Any]) -> None:
        self._client.queued_request(request)

    def flush(self) -> None:
        """Flush the request queue."""
        self._client.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        self._client.close()
