from __future__ import annotations


def test_top_level_exports_user_facing_symbols() -> None:
    from experiment_tracker_sdk import (
        ExperimentBuilder,
        ExperimentInstance,
        ExperimentStatus,
        ExpTracker,
        ExpTrackerAPIError,
        ExpTrackerConfigError,
        ExpTrackerError,
        ExpTrackerProgressError,
        FeatureNode,
        FeatureNodeLike,
        InitParams,
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
        monkey_patch_tensorboard,
    )
    from experiment_tracker_sdk.client.domain.experiments.dto import (
        ExperimentStatus as ClientExperimentStatus,
    )
    from experiment_tracker_sdk.client.domain.experiments.dto import (
        FeatureNode as ClientFeatureNode,
    )
    from experiment_tracker_sdk.client.domain.experiments.dto import (
        FeatureNodeLike as ClientFeatureNodeLike,
    )
    from experiment_tracker_sdk.client.fetching_domain_pages import (
        fetch_all_project_experiments as source_fetch_all_project_experiments,
    )
    from experiment_tracker_sdk.client.fetching_domain_pages import (
        fetch_all_projects as source_fetch_all_projects,
    )
    from experiment_tracker_sdk.client.fetching_domain_pages import (
        fetch_all_recent_experiments as source_fetch_all_recent_experiments,
    )
    from experiment_tracker_sdk.client.fetching_domain_pages import (
        fetch_all_teams as source_fetch_all_teams,
    )
    from experiment_tracker_sdk.client.instances import (
        ExperimentBuilder as ClientExperimentBuilder,
    )
    from experiment_tracker_sdk.client.instances import (
        ExperimentInstance as ClientExperimentInstance,
    )
    from experiment_tracker_sdk.client.instances import (
        MetricBuilder as ClientMetricBuilder,
    )
    from experiment_tracker_sdk.client.instances import (
        MetricInstance as ClientMetricInstance,
    )
    from experiment_tracker_sdk.client.instances import (
        ProjectBuilder as ClientProjectBuilder,
    )
    from experiment_tracker_sdk.client.instances import (
        ProjectInstance as ClientProjectInstance,
    )
    from experiment_tracker_sdk.client.instances import (
        TeamBuilder as ClientTeamBuilder,
    )
    from experiment_tracker_sdk.client.instances import (
        TeamInstance as ClientTeamInstance,
    )
    from experiment_tracker_sdk.error import (
        ExpTrackerAPIError as SourceAPIError,
    )
    from experiment_tracker_sdk.error import (
        ExpTrackerConfigError as SourceConfigError,
    )
    from experiment_tracker_sdk.error import (
        ExpTrackerError as SourceError,
    )
    from experiment_tracker_sdk.error import (
        ExpTrackerProgressError as SourceProgressError,
    )
    from experiment_tracker_sdk.exp_tracker import ExpTracker as SourceExpTracker
    from experiment_tracker_sdk.utils.content_utils import (
        image_data_to_png_bytes as source_image_data_to_png_bytes,
    )
    from experiment_tracker_sdk.utils.experiment_init_strategy import (
        InitParams as SourceInitParams,
    )
    from experiment_tracker_sdk.utils.hooks.tensorboard import (
        monkey_patch_tensorboard as source_monkey_patch_tensorboard,
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
    assert monkey_patch_tensorboard is source_monkey_patch_tensorboard
    assert ExpTrackerError is SourceError
    assert ExpTrackerConfigError is SourceConfigError
    assert ExpTrackerAPIError is SourceAPIError
    assert ExpTrackerProgressError is SourceProgressError
    assert config.__name__ == "experiment_tracker_sdk.config"


def test_client_exports_request_and_access_symbols() -> None:
    from experiment_tracker_sdk.client import (
        UNSET,
        ApiRequestSpec,
        APIRequestsRegistry,
        ArtifactClient,
        BlobUploadResult,
        ExperimentTrackerClient,
        ExpTrackerApiAccess,
        FileDownloadResponse,
        FileUploadSpec,
        ResolvedClientAndRegistry,
        Unset,
        resolve_client_and_registry,
    )
    from experiment_tracker_sdk.client.api_access import (
        ExpTrackerApiAccess as SourceApiAccess,
    )
    from experiment_tracker_sdk.client.api_access import (
        ResolvedClientAndRegistry as SourceResolvedClientAndRegistry,
    )
    from experiment_tracker_sdk.client.api_access import (
        resolve_client_and_registry as source_resolve_client_and_registry,
    )
    from experiment_tracker_sdk.client.api_registry import (
        APIRequestsRegistry as SourceAPIRequestsRegistry,
    )
    from experiment_tracker_sdk.client.artifact_client import (
        ArtifactClient as SourceArtifactClient,
    )
    from experiment_tracker_sdk.client.artifact_client import (
        BlobUploadResult as SourceBlobUploadResult,
    )
    from experiment_tracker_sdk.client.client import (
        ExperimentTrackerClient as SourceExperimentTrackerClient,
    )
    from experiment_tracker_sdk.client.constants import UNSET as SOURCE_UNSET
    from experiment_tracker_sdk.client.constants import Unset as SourceUnset
    from experiment_tracker_sdk.client.request_types import (
        ApiRequestSpec as SourceApiRequestSpec,
    )
    from experiment_tracker_sdk.client.request_types import (
        FileDownloadResponse as SourceFileDownloadResponse,
    )
    from experiment_tracker_sdk.client.request_types import (
        FileUploadSpec as SourceFileUploadSpec,
    )

    assert ExperimentTrackerClient is SourceExperimentTrackerClient
    assert APIRequestsRegistry is SourceAPIRequestsRegistry
    assert ArtifactClient is SourceArtifactClient
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
    from experiment_tracker_sdk.client import domain as source_domain
    from experiment_tracker_sdk.client import instances as source_instances

    assert ExperimentBuilder is source_instances.ExperimentBuilder
    assert ExperimentInstance is source_instances.ExperimentInstance
    assert MetricBuilder is source_instances.MetricBuilder
    assert MetricInstance is source_instances.MetricInstance
    assert ProjectBuilder is source_instances.ProjectBuilder
    assert ProjectInstance is source_instances.ProjectInstance
    assert TeamBuilder is source_instances.TeamBuilder
    assert TeamInstance is source_instances.TeamInstance
    assert HealthRequestSpecFactory is source_domain.HealthRequestSpecFactory
    assert HealthService is source_domain.HealthService
    assert ExperimentRequestSpecFactory is source_domain.ExperimentRequestSpecFactory
    assert ExperimentService is source_domain.ExperimentService
    assert ExperimentArtifactsRequestSpecFactory is (
        source_domain.ExperimentArtifactsRequestSpecFactory
    )
    assert ExperimentArtifactsService is source_domain.ExperimentArtifactsService
    assert HypothesisRequestSpecFactory is source_domain.HypothesisRequestSpecFactory
    assert HypothesisService is source_domain.HypothesisService
    assert MetricRequestSpecFactory is source_domain.MetricRequestSpecFactory
    assert MetricService is source_domain.MetricService
    assert ProjectArtifactsRequestSpecFactory is (
        source_domain.ProjectArtifactsRequestSpecFactory
    )
    assert ProjectArtifactsService is source_domain.ProjectArtifactsService
    assert ProjectRequestSpecFactory is source_domain.ProjectRequestSpecFactory
    assert ProjectService is source_domain.ProjectService
    assert ScalarsRequestSpecFactory is source_domain.ScalarsRequestSpecFactory
    assert ScalarsService is source_domain.ScalarsService
    assert TeamRequestSpecFactory is source_domain.TeamRequestSpecFactory
    assert TeamService is source_domain.TeamService
    assert UserRequestSpecFactory is source_domain.UserRequestSpecFactory
    assert UserService is source_domain.UserService
