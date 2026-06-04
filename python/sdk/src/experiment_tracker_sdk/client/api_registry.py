from __future__ import annotations

from experiment_tracker_sdk.client.domain import (
    ExperimentArtifactsRequestSpecFactory,
    ExperimentDataRequestSpecFactory,
    ExperimentRequestSpecFactory,
    HealthRequestSpecFactory,
    HypothesisRequestSpecFactory,
    MetricRequestSpecFactory,
    ProjectArtifactsRequestSpecFactory,
    ProjectRequestSpecFactory,
    ScalarsRequestSpecFactory,
    TeamRequestSpecFactory,
    UserRequestSpecFactory,
)


class APIRequestsRegistry:
    """Container for all SDK request-spec factories.

    Args:
        None. The registry constructs one stateless factory per API domain.

    Result:
        Object exposing typed properties for experiments, metrics, projects,
        artifacts, experiment data, users, and health endpoints.
    """

    def __init__(self):
        """Instantiate request-spec factories for every API domain.

        Args:
            None.

        Returns:
            None. Factories are stored on private attributes and exposed through
            read-only properties.
        """
        self._experiment_service = ExperimentRequestSpecFactory()
        self._metric_service = MetricRequestSpecFactory()
        self._project_service = ProjectRequestSpecFactory()
        self._scalars_service = ScalarsRequestSpecFactory()
        self._hypothesis_service = HypothesisRequestSpecFactory()
        self._team_service = TeamRequestSpecFactory()
        self._project_artifacts_service = ProjectArtifactsRequestSpecFactory()
        self._experiment_artifacts_service = ExperimentArtifactsRequestSpecFactory()
        self._experiment_data_service = ExperimentDataRequestSpecFactory()
        self._user_service = UserRequestSpecFactory()
        self._health_service = HealthRequestSpecFactory()

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
    def experiment_data(self) -> ExperimentDataRequestSpecFactory:
        """Return request builders for experiment snapshot metadata endpoints.

        Args:
            None.

        Returns:
            The experiment-data request-spec factory registered on this API
            registry instance.
        """
        return self._experiment_data_service

    @property
    def users(self) -> UserRequestSpecFactory:
        return self._user_service

    @property
    def health(self) -> HealthRequestSpecFactory:
        return self._health_service
