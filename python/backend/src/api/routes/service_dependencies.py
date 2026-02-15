from domain.scalars.dependencies import get_scalars_service
from domain.scalars.service import ScalarsService, ScalarsServiceProtocol
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

from domain.metrics.repository import MetricRepository
from domain.metrics.service import MetricService

from domain.projects.repository import ProjectRepository
from domain.projects.service import ProjectService

from domain.team.teams.repository import TeamRepository
from domain.team.teams.service import TeamService


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
    return ExperimentService(
        db=session,
        experiment_repository=experiment_repository,
        permission_checker=permission_checker,
    )


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
) -> TeamService:
    return TeamService(
        session,
        team_repository=team_repository,
        permission_checker=permission_checker,
        permission_service=permission_service,
    )


# Project Service Dependencies


async def get_project_service(
    session: AsyncSession = Depends(get_async_session),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
    permission_service: PermissionService = Depends(get_permission_service),
    project_repository: ProjectRepository = Depends(get_project_repository),
    team_repository: TeamRepository = Depends(get_team_repository),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
) -> ProjectService:
    return ProjectService(
        session,
        permission_checker=permission_checker,
        permission_service=permission_service,
        project_repository=project_repository,
        team_repository=team_repository,
        scalars_service=scalars_service,
    )
