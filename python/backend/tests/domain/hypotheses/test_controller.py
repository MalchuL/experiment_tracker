"""
Tests for the hypotheses controller (API endpoints).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual
from db.database import get_async_session
from domain.hypotheses.controller import router as hypotheses_router
from domain.projects.controller import router as projects_router
from domain.scalars.dependencies import get_scalars_service
from domain.scalars.service import NoOpScalarsService
from domain.team.teams.controller import router as teams_router
from models import User


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(teams_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(hypotheses_router, prefix="/api/v1")
    return app


@pytest.fixture
def test_app(db_session: AsyncSession, test_user: User) -> FastAPI:
    app = create_test_app()

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return test_user

    async def override_scalars_service():
        return NoOpScalarsService()

    app.dependency_overrides[get_async_session] = override_get_db
    app.dependency_overrides[get_current_user_dual] = override_current_user
    app.dependency_overrides[get_scalars_service] = override_scalars_service
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)


@pytest.fixture
def auth_client(test_app: FastAPI):
    def _get_auth_client(user: User) -> TestClient:
        async def override_current_user():
            return user

        test_app.dependency_overrides[get_current_user_dual] = override_current_user
        return TestClient(test_app)

    return _get_auth_client


def _create_team(client: TestClient, name: str = "Hypothesis Team") -> str:
    response = client.post(
        "/api/v1/teams",
        json={"name": name, "description": "Team for hypothesis tests"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def _add_team_member(
    client: TestClient, team_id: str, user_id: str, role: str
) -> None:
    response = client.post(
        "/api/v1/teams/members",
        json={"teamId": team_id, "userId": user_id, "role": role},
    )
    assert response.status_code == 200


def _create_project(client: TestClient, team_id: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Hypothesis Project",
            "description": "Project for hypotheses",
            "teamId": team_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_hypothesis(client: TestClient, project_id: str) -> dict:
    response = client.post(
        "/api/v1/hypotheses",
        json={
            "projectId": project_id,
            "title": "Increase conversion",
            "description": "Hypothesis description",
            "author": "tester",
            "targetMetrics": ["conversion_rate"],
        },
    )
    assert response.status_code == 200
    return response.json()


class TestHypothesisControllerCreate:
    async def test_create_hypothesis_as_member(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="member")
        project = _create_project(owner_client, team_id)

        member_client = auth_client(test_user_2)
        response = member_client.post(
            "/api/v1/hypotheses",
            json={
                "projectId": project["id"],
                "title": "Member hypothesis",
                "description": "Member created",
                "author": "member",
                "targetMetrics": ["lift"],
            },
        )

        assert response.status_code == 200
        assert response.json()["projectId"] == project["id"]

    async def test_create_hypothesis_denied_for_viewer(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="viewer")
        project = _create_project(owner_client, team_id)

        viewer_client = auth_client(test_user_2)
        response = viewer_client.post(
            "/api/v1/hypotheses",
            json={
                "projectId": project["id"],
                "title": "Viewer hypothesis",
                "description": "Viewer created",
                "author": "viewer",
                "targetMetrics": ["lift"],
            },
        )

        assert response.status_code == 403


class TestHypothesisControllerAccess:
    async def test_get_hypothesis_accessible_for_viewer(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="viewer")
        project = _create_project(owner_client, team_id)
        hypothesis = _create_hypothesis(owner_client, project["id"])

        viewer_client = auth_client(test_user_2)
        response = viewer_client.get(f"/api/v1/hypotheses/{hypothesis['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == hypothesis["id"]

    async def test_update_hypothesis_denied_for_viewer(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="viewer")
        project = _create_project(owner_client, team_id)
        hypothesis = _create_hypothesis(owner_client, project["id"])

        viewer_client = auth_client(test_user_2)
        response = viewer_client.patch(
            f"/api/v1/hypotheses/{hypothesis['id']}",
            json={"description": "Viewer update"},
        )

        assert response.status_code == 403

    async def test_delete_hypothesis_denied_for_viewer(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="viewer")
        project = _create_project(owner_client, team_id)
        hypothesis = _create_hypothesis(owner_client, project["id"])

        viewer_client = auth_client(test_user_2)
        response = viewer_client.delete(f"/api/v1/hypotheses/{hypothesis['id']}")

        assert response.status_code == 403

    async def test_get_recent_hypotheses_for_project(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="viewer")
        project = _create_project(owner_client, team_id)
        first = owner_client.post(
            "/api/v1/hypotheses",
            json={
                "projectId": project["id"],
                "title": "First hypothesis",
                "description": "First description",
                "author": "owner",
                "targetMetrics": ["conversion_rate"],
            },
        )
        assert first.status_code == 200
        second = owner_client.post(
            "/api/v1/hypotheses",
            json={
                "projectId": project["id"],
                "title": "Second hypothesis",
                "description": "Second description",
                "author": "owner",
                "targetMetrics": ["retention_rate"],
            },
        )
        assert second.status_code == 200

        viewer_client = auth_client(test_user_2)
        response = viewer_client.get(
            f"/api/v1/hypotheses/recent?projectId={project['id']}&limit=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == second.json()["id"]
