from .dto import DashboardStatsDTO
from fastapi import APIRouter
from fastapi import Depends
from db.database import get_async_session
from api.routes.auth import get_current_user_dual, require_api_token_scopes
from models import User
from domain.rbac.permissions import ProjectActions
from sqlalchemy.ext.asyncio import AsyncSession
from domain.projects.dashboard.service import DashboardService
from uuid import UUID

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
) -> DashboardStatsDTO:
    return await DashboardService(session).get_dashboard_stats(user, project_id)
