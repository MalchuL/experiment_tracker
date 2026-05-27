from __future__ import annotations


def test_top_level_exports_user_facing_symbols() -> None:
    from experiment_tracker_sdk import (
        ExpTracker,
        ExpTrackerAPIError,
        ExpTrackerConfigError,
        ExpTrackerError,
        ExpTrackerProgressError,
        ExperimentStatus,
        FeatureNode,
        FeatureNodeLike,
        InitParams,
        ExperimentBuilder,
        ExperimentInstance,
        MetricBuilder,
        MetricInstance,
        ProjectBuilder,
        ProjectInstance,
        TeamBuilder,
        TeamInstance,
        config,
        fetch_all_project_experiments,
        fetch_all_projects,
        fetch_all_recent_experiments,
        fetch_all_teams,
        image_data_to_png_bytes,
    )
    from experiment_tracker_sdk.client.fetching_domain_pages import (
        fetch_all_project_experiments as source_fetch_all_project_experiments,
        fetch_all_projects as source_fetch_all_projects,
        fetch_all_recent_experiments as source_fetch_all_recent_experiments,
        fetch_all_teams as source_fetch_all_teams,
    )
    from experiment_tracker_sdk.client.instances import (
        ExperimentBuilder as ClientExperimentBuilder,
        ExperimentInstance as ClientExperimentInstance,
        MetricBuilder as ClientMetricBuilder,
        MetricInstance as ClientMetricInstance,
        ProjectBuilder as ClientProjectBuilder,
        ProjectInstance as ClientProjectInstance,
        TeamBuilder as ClientTeamBuilder,
        TeamInstance as ClientTeamInstance,
    )
    from experiment_tracker_sdk.client.domain.experiments.dto import (
        ExperimentStatus as ClientExperimentStatus,
        FeatureNode as ClientFeatureNode,
        FeatureNodeLike as ClientFeatureNodeLike,
    )
    from experiment_tracker_sdk.error import (
        ExpTrackerAPIError as SourceAPIError,
        ExpTrackerConfigError as SourceConfigError,
        ExpTrackerError as SourceError,
        ExpTrackerProgressError as SourceProgressError,
    )
    from experiment_tracker_sdk.exp_tracker import ExpTracker as SourceExpTracker
    from experiment_tracker_sdk.utils.content_utils import (
        image_data_to_png_bytes as source_image_data_to_png_bytes,
    )
    from experiment_tracker_sdk.utils.experiment_init_strategy import (
        InitParams as SourceInitParams,
    )

    assert ExpTracker is SourceExpTracker
    assert InitParams is SourceInitParams
    assert ExperimentStatus is ClientExperimentStatus
    assert FeatureNode is ClientFeatureNode
    assert FeatureNodeLike == ClientFeatureNodeLike
    assert ExperimentBuilder is ClientExperimentBuilder
    assert ExperimentInstance is ClientExperimentInstance
    assert MetricBuilder is ClientMetricBuilder
    assert MetricInstance is ClientMetricInstance
    assert ProjectBuilder is ClientProjectBuilder
    assert ProjectInstance is ClientProjectInstance
    assert TeamBuilder is ClientTeamBuilder
    assert TeamInstance is ClientTeamInstance
    assert fetch_all_project_experiments is source_fetch_all_project_experiments
    assert fetch_all_projects is source_fetch_all_projects
    assert fetch_all_recent_experiments is source_fetch_all_recent_experiments
    assert fetch_all_teams is source_fetch_all_teams
    assert image_data_to_png_bytes is source_image_data_to_png_bytes
    assert ExpTrackerError is SourceError
    assert ExpTrackerConfigError is SourceConfigError
    assert ExpTrackerAPIError is SourceAPIError
    assert ExpTrackerProgressError is SourceProgressError
    assert config.__name__ == "experiment_tracker_sdk.config"


def test_client_exports_request_and_access_symbols() -> None:
    from experiment_tracker_sdk.client import (
        APIRequestsRegistry,
        ApiRequestSpec,
        BlobRequestsStrategy,
        BlobUploadResult,
        ExpTrackerApiAccess,
        ExperimentTrackerClient,
        FileDownloadResponse,
        FileUploadSpec,
        ResolvedClientAndRegistry,
        UNSET,
        Unset,
        resolve_client_and_registry,
    )
    from experiment_tracker_sdk.client.api_access import (
        ExpTrackerApiAccess as SourceApiAccess,
        ResolvedClientAndRegistry as SourceResolvedClientAndRegistry,
        resolve_client_and_registry as source_resolve_client_and_registry,
    )
    from experiment_tracker_sdk.client.api_registry import (
        APIRequestsRegistry as SourceAPIRequestsRegistry,
    )
    from experiment_tracker_sdk.client.blob_api import (
        BlobRequestsStrategy as SourceBlobRequestsStrategy,
        BlobUploadResult as SourceBlobUploadResult,
    )
    from experiment_tracker_sdk.client.client import (
        ExperimentTrackerClient as SourceExperimentTrackerClient,
    )
    from experiment_tracker_sdk.client.constants import UNSET as SOURCE_UNSET
    from experiment_tracker_sdk.client.constants import Unset as SourceUnset
    from experiment_tracker_sdk.client.request_types import (
        ApiRequestSpec as SourceApiRequestSpec,
        FileDownloadResponse as SourceFileDownloadResponse,
        FileUploadSpec as SourceFileUploadSpec,
    )

    assert ExperimentTrackerClient is SourceExperimentTrackerClient
    assert APIRequestsRegistry is SourceAPIRequestsRegistry
    assert BlobRequestsStrategy is SourceBlobRequestsStrategy
    assert BlobUploadResult is SourceBlobUploadResult
    assert ExpTrackerApiAccess is SourceApiAccess
    assert ResolvedClientAndRegistry is SourceResolvedClientAndRegistry
    assert resolve_client_and_registry is source_resolve_client_and_registry
    assert ApiRequestSpec is SourceApiRequestSpec
    assert FileDownloadResponse is SourceFileDownloadResponse
    assert FileUploadSpec is SourceFileUploadSpec
    assert UNSET is SOURCE_UNSET
    assert Unset is SourceUnset


def test_client_exports_instances_and_domain_services() -> None:
    from experiment_tracker_sdk.client import (
        ExperimentArtifactsRequestSpecFactory,
        ExperimentArtifactsService,
        ExperimentBuilder,
        ExperimentInstance,
        ExperimentRequestSpecFactory,
        ExperimentService,
        HealthRequestSpecFactory,
        HealthService,
        HypothesisRequestSpecFactory,
        HypothesisService,
        MetricBuilder,
        MetricInstance,
        MetricRequestSpecFactory,
        MetricService,
        ProjectArtifactsRequestSpecFactory,
        ProjectArtifactsService,
        ProjectBuilder,
        ProjectInstance,
        ProjectRequestSpecFactory,
        ProjectService,
        ScalarsRequestSpecFactory,
        ScalarsService,
        TeamBuilder,
        TeamInstance,
        TeamRequestSpecFactory,
        TeamService,
        UserRequestSpecFactory,
        UserService,
    )
    from experiment_tracker_sdk.client.domain import (
        ExperimentArtifactsRequestSpecFactory as SourceExperimentArtifactsRequestSpecFactory,
        ExperimentArtifactsService as SourceExperimentArtifactsService,
        ExperimentRequestSpecFactory as SourceExperimentRequestSpecFactory,
        ExperimentService as SourceExperimentService,
        HealthRequestSpecFactory as SourceHealthRequestSpecFactory,
        HealthService as SourceHealthService,
        HypothesisRequestSpecFactory as SourceHypothesisRequestSpecFactory,
        HypothesisService as SourceHypothesisService,
        MetricRequestSpecFactory as SourceMetricRequestSpecFactory,
        MetricService as SourceMetricService,
        ProjectArtifactsRequestSpecFactory as SourceProjectArtifactsRequestSpecFactory,
        ProjectArtifactsService as SourceProjectArtifactsService,
        ProjectRequestSpecFactory as SourceProjectRequestSpecFactory,
        ProjectService as SourceProjectService,
        ScalarsRequestSpecFactory as SourceScalarsRequestSpecFactory,
        ScalarsService as SourceScalarsService,
        TeamRequestSpecFactory as SourceTeamRequestSpecFactory,
        TeamService as SourceTeamService,
        UserRequestSpecFactory as SourceUserRequestSpecFactory,
        UserService as SourceUserService,
    )
    from experiment_tracker_sdk.client.instances import (
        ExperimentBuilder as SourceExperimentBuilder,
        ExperimentInstance as SourceExperimentInstance,
        MetricBuilder as SourceMetricBuilder,
        MetricInstance as SourceMetricInstance,
        ProjectBuilder as SourceProjectBuilder,
        ProjectInstance as SourceProjectInstance,
        TeamBuilder as SourceTeamBuilder,
        TeamInstance as SourceTeamInstance,
    )

    assert ExperimentBuilder is SourceExperimentBuilder
    assert ExperimentInstance is SourceExperimentInstance
    assert MetricBuilder is SourceMetricBuilder
    assert MetricInstance is SourceMetricInstance
    assert ProjectBuilder is SourceProjectBuilder
    assert ProjectInstance is SourceProjectInstance
    assert TeamBuilder is SourceTeamBuilder
    assert TeamInstance is SourceTeamInstance
    assert HealthRequestSpecFactory is SourceHealthRequestSpecFactory
    assert HealthService is SourceHealthService
    assert ExperimentRequestSpecFactory is SourceExperimentRequestSpecFactory
    assert ExperimentService is SourceExperimentService
    assert ExperimentArtifactsRequestSpecFactory is (
        SourceExperimentArtifactsRequestSpecFactory
    )
    assert ExperimentArtifactsService is SourceExperimentArtifactsService
    assert HypothesisRequestSpecFactory is SourceHypothesisRequestSpecFactory
    assert HypothesisService is SourceHypothesisService
    assert MetricRequestSpecFactory is SourceMetricRequestSpecFactory
    assert MetricService is SourceMetricService
    assert ProjectArtifactsRequestSpecFactory is (
        SourceProjectArtifactsRequestSpecFactory
    )
    assert ProjectArtifactsService is SourceProjectArtifactsService
    assert ProjectRequestSpecFactory is SourceProjectRequestSpecFactory
    assert ProjectService is SourceProjectService
    assert ScalarsRequestSpecFactory is SourceScalarsRequestSpecFactory
    assert ScalarsService is SourceScalarsService
    assert TeamRequestSpecFactory is SourceTeamRequestSpecFactory
    assert TeamService is SourceTeamService
    assert UserRequestSpecFactory is SourceUserRequestSpecFactory
    assert UserService is SourceUserService
