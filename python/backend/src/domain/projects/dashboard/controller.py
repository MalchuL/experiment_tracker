from .dto import DashboardStatsDTO
from fastapi import APIRouter
from fastapi import Depends
from db.database import get_async_session
from api.routes.auth import current_active_user
from models import User
from sqlalchemy.ext.asyncio import AsyncSession
from domain.projects.dashboard.service import DashboardService
from uuid import UUID

router = APIRouter(
    dependencies=[Depends(current_active_user)], prefix="/dashboard", tags=["dashboard"]
)


# TODO cover with tests
@router.get("/project/{project_id}/stats")
async def get_dashboard_stats(
    project_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> DashboardStatsDTO:
    return await DashboardService(session).get_dashboard_stats(user, project_id)
