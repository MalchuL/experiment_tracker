from experiment_tracker_sdk.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.request import ApiRequestSpec
from experiment_tracker_sdk.client.domain import (
    ExperimentArtifactsRequestSpecFactory,
    ExperimentRequestSpecFactory,
    MetricRequestSpecFactory,
    ProjectRequestSpecFactory,
    ProjectArtifactsRequestSpecFactory,
    ScalarsRequestSpecFactory,
    HypothesisRequestSpecFactory,
    TeamRequestSpecFactory,
)
from experiment_tracker_sdk.client.domain.experiment_artifacts.dto import (
    ArtifactType,
    LogArtifactAtStepRequest,
)
from pydantic import BaseModel
from typing import Any, TypeVar, cast
from pathlib import Path

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class API:
    def __init__(self, client: ExperimentTrackerClient):
        self._tracker_client = client
        self._experiment_service = ExperimentRequestSpecFactory()
        self._metric_service = MetricRequestSpecFactory()
        self._project_service = ProjectRequestSpecFactory()
        self._scalars_service = ScalarsRequestSpecFactory()
        self._hypothesis_service = HypothesisRequestSpecFactory()
        self._team_service = TeamRequestSpecFactory()
        self._project_artifacts_service = ProjectArtifactsRequestSpecFactory()
        self._experiment_artifacts_service = ExperimentArtifactsRequestSpecFactory()

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

    @property
    def project_artifacts(self) -> ProjectArtifactsRequestSpecFactory:
        return self._project_artifacts_service

    @property
    def experiment_artifacts(self) -> ExperimentArtifactsRequestSpecFactory:
        return self._experiment_artifacts_service

    def request(
        self, request_spec: ApiRequestSpec[ResponseT]
    ) -> ResponseT | list[ResponseT] | dict[str, Any]:
        return self._tracker_client.request(request_spec)

    def queued_request(self, request_spec: ApiRequestSpec[Any]) -> None:
        self._tracker_client.queued_request(request_spec)

    def flush(self) -> None:
        """Flush the request queue."""
        self._tracker_client.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        self._tracker_client.close()

    def check_project_artifacts(
        self, project_id: str, hashes: list[str]
    ) -> dict[str, Any]:
        response = self.request(
            self.project_artifacts.check_project_artifacts(project_id, hashes)
        )
        if isinstance(response, BaseModel):
            return cast(dict[str, Any], response.model_dump())
        return cast(dict[str, Any], response)
