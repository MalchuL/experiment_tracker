import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import current_active_user
from db.database import get_async_session
from domain.projects.dashboard.controller import router as dashboard_router
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from models import Experiment, ExperimentStatus, Hypothesis, HypothesisStatus, Project, User


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(dashboard_router, prefix="/api/v1")
    return app


@pytest.fixture
def test_app(db_session: AsyncSession, test_user: User) -> FastAPI:
    app = create_test_app()

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return test_user

    app.dependency_overrides[get_async_session] = override_get_db
    app.dependency_overrides[current_active_user] = override_current_user
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)


async def _create_project(db_session: AsyncSession, owner: User) -> Project:
    project = Project(
        name="Dashboard Controller Project",
        description="Controller test project",
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
        description="Controller experiment",
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
        description="Controller hypothesis",
        author="tester",
        status=status,
        target_metrics=["conversion"],
    )
    db_session.add(hypothesis)
    await db_session.flush()
    return hypothesis


class TestDashboardController:
    async def test_get_dashboard_stats(
        self,
        client: TestClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        project = await _create_project(db_session, test_user)
        await _create_experiment(db_session, project, ExperimentStatus.RUNNING)
        await _create_experiment(db_session, project, ExperimentStatus.COMPLETE)
        await _create_hypothesis(db_session, project, HypothesisStatus.SUPPORTED)
        await _create_hypothesis(db_session, project, HypothesisStatus.REFUTED)

        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )

        response = client.get(f"/api/v1/dashboard/project/{project.id}/stats")

        assert response.status_code == 200
        payload = response.json()
        assert payload["totalExperiments"] == 2
        assert payload["runningExperiments"] == 1
        assert payload["completedExperiments"] == 1
        assert payload["failedExperiments"] == 0
        assert payload["totalHypotheses"] == 2
        assert payload["supportedHypotheses"] == 1
        assert payload["refutedHypotheses"] == 1
