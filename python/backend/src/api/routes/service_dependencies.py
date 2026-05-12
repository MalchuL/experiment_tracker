from config.settings import get_settings
from clients.artifacts_info import (
    ArtifactsInfoClient,
    ArtifactsInfoResultDTO,
    LogArtifactResponseDTO,
)
from domain.experiment_artifacts.noop_service import NoOpExperimentArtifactsService
from domain.experiment_artifacts.protocol import ExperimentArtifactsServiceProtocol
from domain.experiment_artifacts.service import ExperimentArtifactsService
from domain.project_artifacts.noop_service import NoOpProjectArtifactsService
from domain.project_artifacts.protocol import ProjectArtifactsServiceProtocol
from domain.project_artifacts.service import ProjectArtifactsService
from clients.object_storage import ObjectStorageClient
from clients.scalars import ScalarsServiceClient
from domain.scalars.service import (
    NoOpScalarsService,
    ScalarsService,
    ScalarsServiceProtocol,
)
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_async_session
from domain.api_tokens.repository import ApiTokenRepository
from domain.api_tokens.service import ApiTokenService

from domain.rbac.repository import PermissionRepository
from domain.rbac.wrapper import PermissionChecker
from domain.rbac.service import PermissionService

from domain.experiments.repository import ExperimentRepository
from domain.experiments.service import ExperimentService

from domain.hypotheses.repository import HypothesisRepository
from domain.hypotheses.service import HypothesisService

from domain.project_reports.repository import ProjectReportRepository
from domain.project_reports.service import ProjectReportService

from domain.metrics.repository import MetricRepository
from domain.metrics.service import MetricService

from domain.projects.members.service import ProjectMembersService
from domain.projects.repository import ProjectRepository
from domain.projects.service import ProjectService

from domain.team.teams.repository import TeamRepository
from domain.team.teams.service import TeamService


class _NoOpArtifactsInfoClient:
    async def get_artifacts(self, *args, **kwargs) -> ArtifactsInfoResultDTO:
        return ArtifactsInfoResultDTO(data=[], total=0)

    async def log_artifact_at_step(self, *args, **kwargs) -> LogArtifactResponseDTO:
        return LogArtifactResponseDTO(status="logged")


async def get_project_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectRepository:
    return ProjectRepository(session)


async def get_permission_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PermissionRepository:
    return PermissionRepository(session)


async def get_permission_service(
    session: AsyncSession = Depends(get_async_session),
    permission_repository: PermissionRepository = Depends(get_permission_repository),
    project_repository: ProjectRepository = Depends(get_project_repository),
) -> PermissionService:
    return PermissionService(session, permission_repository, project_repository)


async def get_permission_checker(
    session: AsyncSession = Depends(get_async_session),
    permission_service: PermissionService = Depends(get_permission_service),
) -> PermissionChecker:
    return PermissionChecker(session, permission_service)


# API Token Service Dependencies


async def get_api_token_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ApiTokenRepository:
    return ApiTokenRepository(db=session)


async def get_api_token_service(
    session: AsyncSession = Depends(get_async_session),
    api_token_repository: ApiTokenRepository = Depends(get_api_token_repository),
) -> ApiTokenService:
    return ApiTokenService(db=session, api_token_repository=api_token_repository)


# Experiment Service Dependencies


async def get_experiment_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ExperimentRepository:
    return ExperimentRepository(db=session)


async def get_experiment_service(
    session: AsyncSession = Depends(get_async_session),
    experiment_repository: ExperimentRepository = Depends(get_experiment_repository),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
) -> ExperimentService:
    settings = get_settings()
    scalars_service: ScalarsServiceProtocol
    if settings.scalars_service_url:
        scalars_service = ScalarsService(
            ScalarsServiceClient(settings.scalars_service_url),
            permission_checker,
            experiment_repository,
        )
    else:
        scalars_service = NoOpScalarsService()
    object_storage_client = (
        ObjectStorageClient(settings.object_storage_service_url)
        if settings.object_storage_service_url
        else None
    )
    service = ExperimentService(
        db=session,
        experiment_repository=experiment_repository,
        permission_checker=permission_checker,
    )
    service.scalars_service = scalars_service
    service.object_storage_client = object_storage_client
    return service


async def get_scalars_service(
    permission_checker: PermissionChecker = Depends(get_permission_checker),
    experiment_repository: ExperimentRepository = Depends(get_experiment_repository),
) -> ScalarsServiceProtocol:
    settings = get_settings()
    scalars_service_url = settings.scalars_service_url
    if scalars_service_url:
        client = ScalarsServiceClient(scalars_service_url)
        return ScalarsService(client, permission_checker, experiment_repository)
    else:
        return NoOpScalarsService()


async def get_experiment_artifacts_service(
    permission_checker: PermissionChecker = Depends(get_permission_checker),
    experiment_repository: ExperimentRepository = Depends(get_experiment_repository),
) -> ExperimentArtifactsServiceProtocol:
    settings = get_settings()
    scalars_url = settings.scalars_service_url
    object_storage_url = settings.object_storage_service_url
    if object_storage_url:
        obj_client = ObjectStorageClient(object_storage_url)
        artifacts_client = (
            ArtifactsInfoClient(scalars_url)
            if scalars_url
            else _NoOpArtifactsInfoClient()
        )
        return ExperimentArtifactsService(
            object_storage_client=obj_client,
            artifacts_info_at_step_client=artifacts_client,
            permission_checker=permission_checker,
            experiment_repository=experiment_repository,
        )
    return NoOpExperimentArtifactsService()


async def get_project_artifacts_service(
    permission_checker: PermissionChecker = Depends(get_permission_checker),
) -> ProjectArtifactsServiceProtocol:
    settings = get_settings()
    object_storage_url = settings.object_storage_service_url
    if object_storage_url:
        obj_client = ObjectStorageClient(object_storage_url)
        return ProjectArtifactsService(
            object_storage_client=obj_client,
            permission_checker=permission_checker,
        )
    return NoOpProjectArtifactsService()


# Hypothesis Service Dependencies


async def get_hypothesis_repository(
    session: AsyncSession = Depends(get_async_session),
) -> HypothesisRepository:
    return HypothesisRepository(db=session)


async def get_hypothesis_service(
    session: AsyncSession = Depends(get_async_session),
    hypothesis_repository: HypothesisRepository = Depends(get_hypothesis_repository),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
) -> HypothesisService:
    return HypothesisService(
        db=session,
        hypothesis_repository=hypothesis_repository,
        permission_checker=permission_checker,
    )


async def get_project_report_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectReportRepository:
    return ProjectReportRepository(db=session)


async def get_project_report_service(
    session: AsyncSession = Depends(get_async_session),
    report_repository: ProjectReportRepository = Depends(get_project_report_repository),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
) -> ProjectReportService:
    return ProjectReportService(
        db=session,
        report_repository=report_repository,
        permission_checker=permission_checker,
    )


# Metric Service Dependencies


async def get_metric_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MetricRepository:
    return MetricRepository(db=session)


async def get_metric_service(
    session: AsyncSession = Depends(get_async_session),
    metric_repository: MetricRepository = Depends(get_metric_repository),
    experiment_repository: ExperimentRepository = Depends(get_experiment_repository),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
) -> MetricService:
    return MetricService(
        db=session,
        metric_repository=metric_repository,
        experiment_repository=experiment_repository,
        permission_checker=permission_checker,
    )


# Team Service Dependencies


async def get_team_repository(
    session: AsyncSession = Depends(get_async_session),
) -> TeamRepository:
    return TeamRepository(session)


async def get_team_service(
    session: AsyncSession = Depends(get_async_session),
    team_repository: TeamRepository = Depends(get_team_repository),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
    permission_service: PermissionService = Depends(get_permission_service),
    project_repository: ProjectRepository = Depends(get_project_repository),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
) -> TeamService:
    settings = get_settings()
    object_storage_client = (
        ObjectStorageClient(settings.object_storage_service_url)
        if settings.object_storage_service_url
        else None
    )
    service = TeamService(
        session,
        team_repository=team_repository,
        permission_checker=permission_checker,
        permission_service=permission_service,
    )
    service.project_repository = project_repository
    service.scalars_service = scalars_service
    service.object_storage_client = object_storage_client
    return service


# Project Service Dependencies


async def get_project_service(
    session: AsyncSession = Depends(get_async_session),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
    permission_service: PermissionService = Depends(get_permission_service),
    project_repository: ProjectRepository = Depends(get_project_repository),
    team_repository: TeamRepository = Depends(get_team_repository),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
) -> ProjectService:
    settings = get_settings()
    object_storage_client = (
        ObjectStorageClient(settings.object_storage_service_url)
        if settings.object_storage_service_url
        else None
    )
    service = ProjectService(
        session,
        permission_checker=permission_checker,
        permission_service=permission_service,
        project_repository=project_repository,
        team_repository=team_repository,
        scalars_service=scalars_service,
    )
    service.object_storage_client = object_storage_client
    return service


async def get_project_members_service(
    session: AsyncSession = Depends(get_async_session),
    project_repository: ProjectRepository = Depends(get_project_repository),
    permission_repository: PermissionRepository = Depends(get_permission_repository),
    permission_service: PermissionService = Depends(get_permission_service),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
) -> ProjectMembersService:
    return ProjectMembersService(
        db=session,
        project_repository=project_repository,
        permission_repository=permission_repository,
        permission_service=permission_service,
        permission_checker=permission_checker,
    )
