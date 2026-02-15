from .dto import DashboardStatsDTO
from fastapi import APIRouter
from fastapi import Depends
from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import (
    get_permission_checker,
    get_experiment_repository,
    get_hypothesis_repository,
    get_async_session,
)
from models import User
from domain.rbac.permissions import ProjectActions
from sqlalchemy.ext.asyncio import AsyncSession
from domain.projects.dashboard.service import DashboardService
from uuid import UUID
from domain.rbac.wrapper import PermissionChecker
from domain.experiments.repository import ExperimentRepository
from domain.hypotheses.repository import HypothesisRepository

router = APIRouter(
    dependencies=[
        Depends(get_current_user_dual),
        Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    ],
    prefix="/dashboard",
    tags=["dashboard"],
)


@router.get("/project/{project_id}/stats")
async def get_dashboard_stats(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    session: AsyncSession = Depends(get_async_session),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
    experiment_repository: ExperimentRepository = Depends(get_experiment_repository),
    hypothesis_repository: HypothesisRepository = Depends(get_hypothesis_repository),
) -> DashboardStatsDTO:
    return await DashboardService(
        session=session,
        permission_checker=permission_checker,
        experiment_repository=experiment_repository,
        hypothesis_repository=hypothesis_repository,
    ).get_dashboard_stats(user, project_id)
