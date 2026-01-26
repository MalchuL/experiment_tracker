from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from .dto import DashboardStatsDTO
from domain.experiments.repository import ExperimentRepository
from lib.types import UUID_TYPE
from models import ExperimentStatus, HypothesisStatus
from domain.hypotheses.repository import HypothesisRepository
from domain.rbac.wrapper import PermissionChecker
from domain.projects.errors import ProjectNotAccessibleError


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.permission_checker = PermissionChecker(session)

    async def get_dashboard_stats(
        self, user: User, project_id: UUID_TYPE
    ) -> DashboardStatsDTO:
        if not await self.permission_checker.can_view_project(user.id, project_id):
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        experiments_repository = ExperimentRepository(self.session)
        experiments = await experiments_repository.get_experiments_by_project(
            project_id
        )
        hypotheses_repository = HypothesisRepository(self.session)
        hypotheses = await hypotheses_repository.get_hypotheses_by_project(project_id)
        return DashboardStatsDTO(
            totalExperiments=len(experiments),
            runningExperiments=len(
                [e for e in experiments if e.status == ExperimentStatus.RUNNING]
            ),
            completedExperiments=len(
                [e for e in experiments if e.status == ExperimentStatus.COMPLETE]
            ),
            failedExperiments=len(
                [e for e in experiments if e.status == ExperimentStatus.FAILED]
            ),
            totalHypotheses=len(hypotheses),
            supportedHypotheses=len(
                [h for h in hypotheses if h.status == HypothesisStatus.SUPPORTED]
            ),
            refutedHypotheses=len(
                [h for h in hypotheses if h.status == HypothesisStatus.REFUTED]
            ),
        )
