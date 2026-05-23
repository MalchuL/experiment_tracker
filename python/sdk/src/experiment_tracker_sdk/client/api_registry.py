from __future__ import annotations

from experiment_tracker_sdk.client.domain import (
    ExperimentArtifactsRequestSpecFactory,
    ExperimentRequestSpecFactory,
    HypothesisRequestSpecFactory,
    MetricRequestSpecFactory,
    ProjectArtifactsRequestSpecFactory,
    ProjectRequestSpecFactory,
    ScalarsRequestSpecFactory,
    TeamRequestSpecFactory,
    UserRequestSpecFactory,
)


class APIRequestsRegistry:
    def __init__(self):
        self._experiment_service = ExperimentRequestSpecFactory()
        self._metric_service = MetricRequestSpecFactory()
        self._project_service = ProjectRequestSpecFactory()
        self._scalars_service = ScalarsRequestSpecFactory()
        self._hypothesis_service = HypothesisRequestSpecFactory()
        self._team_service = TeamRequestSpecFactory()
        self._project_artifacts_service = ProjectArtifactsRequestSpecFactory()
        self._experiment_artifacts_service = ExperimentArtifactsRequestSpecFactory()
        self._user_service = UserRequestSpecFactory()

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

    @property
    def users(self) -> UserRequestSpecFactory:
        return self._user_service
