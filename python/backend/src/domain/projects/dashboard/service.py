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
    """Read-only aggregate service for project dashboard statistics.

    The service loads experiments and hypotheses for a project, enforces project view
    permission, and computes lightweight counts for the dashboard landing view.
    """

    def __init__(
        self,
        session: AsyncSession,
        permission_checker: PermissionChecker,
        experiment_repository: ExperimentRepository,
        hypothesis_repository: HypothesisRepository,
    ):
        self.session = session
        self.permission_checker = permission_checker
        self.experiment_repository = experiment_repository
        self.hypothesis_repository = hypothesis_repository

    async def get_dashboard_stats(
        self, user: User, project_id: UUID_TYPE
    ) -> DashboardStatsDTO:
        """Compute status counts for a project dashboard.

        Args:
            user: User requesting dashboard statistics.
            project_id: Project whose dashboard should be summarized.

        Returns:
            DashboardStatsDTO: Total and status-specific experiment/hypothesis counts.

        Raises:
            ProjectNotAccessibleError: If the user cannot view the project.
        """
        if not await self.permission_checker.can_view_project(user.id, project_id):
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        experiments = (
            await self.experiment_repository.get_experiments_by_project(project_id)
        ).data
        hypotheses = (
            await self.hypothesis_repository.get_hypotheses_by_project(project_id)
        ).data
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
