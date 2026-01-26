import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.dashboard.service import DashboardService
from domain.projects.errors import ProjectNotAccessibleError
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from models import Experiment, ExperimentStatus, Hypothesis, HypothesisStatus, Project, User


async def _create_project(db_session: AsyncSession, owner: User) -> Project:
    project = Project(
        name="Dashboard Project",
        description="Project for dashboard tests",
        owner_id=owner.id,
        team_id=None,
        metrics=[],
        settings={},
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


async def _create_experiment(
    db_session: AsyncSession, project: Project, status: ExperimentStatus
) -> Experiment:
    experiment = Experiment(
        project_id=project.id,
        name=f"{status.value}-experiment",
        description="Dashboard experiment",
        status=status,
    )
    db_session.add(experiment)
    await db_session.flush()
    return experiment


async def _create_hypothesis(
    db_session: AsyncSession, project: Project, status: HypothesisStatus
) -> Hypothesis:
    hypothesis = Hypothesis(
        project_id=project.id,
        title=f"{status.value} hypothesis",
        description="Dashboard hypothesis",
        author="tester",
        status=status,
        target_metrics=["conversion"],
    )
    db_session.add(hypothesis)
    await db_session.flush()
    return hypothesis


class TestDashboardService:
    @pytest.fixture
    def dashboard_service(self, db_session: AsyncSession) -> DashboardService:
        return DashboardService(db_session)

    async def test_get_dashboard_stats_requires_permission(
        self,
        dashboard_service: DashboardService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        with pytest.raises(ProjectNotAccessibleError):
            await dashboard_service.get_dashboard_stats(test_user, project.id)

    async def test_get_dashboard_stats_counts_statuses(
        self,
        dashboard_service: DashboardService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        await _create_experiment(db_session, project, ExperimentStatus.PLANNED)
        await _create_experiment(db_session, project, ExperimentStatus.RUNNING)
        await _create_experiment(db_session, project, ExperimentStatus.COMPLETE)
        await _create_experiment(db_session, project, ExperimentStatus.FAILED)
        await _create_hypothesis(db_session, project, HypothesisStatus.PROPOSED)
        await _create_hypothesis(db_session, project, HypothesisStatus.SUPPORTED)
        await _create_hypothesis(db_session, project, HypothesisStatus.REFUTED)

        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )

        stats = await dashboard_service.get_dashboard_stats(test_user, project.id)

        assert stats.totalExperiments == 4
        assert stats.runningExperiments == 1
        assert stats.completedExperiments == 1
        assert stats.failedExperiments == 1
        assert stats.totalHypotheses == 3
        assert stats.supportedHypotheses == 1
        assert stats.refutedHypotheses == 1
