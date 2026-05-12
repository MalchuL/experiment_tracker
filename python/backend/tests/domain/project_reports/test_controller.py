"""
Tests for the project reports controller (API endpoints).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual
from db.database import get_async_session
from domain.project_reports.controller import router as reports_router
from domain.projects.controller import router as projects_router
from api.routes.service_dependencies import get_scalars_service
from domain.scalars.service import NoOpScalarsService
from domain.team.teams.controller import router as teams_router
from models import User


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(teams_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
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


def _create_team(client: TestClient, name: str = "Report Team") -> str:
    response = client.post(
        "/api/v1/teams",
        json={"name": name, "description": "Team for report tests"},
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
            "name": "Report Project",
            "description": "Project for reports",
            "teamId": team_id,
        },
    )
    assert response.status_code == 200
    return response.json()


class TestProjectReportsController:
    async def test_create_list_get_update_report(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="member")
        project = _create_project(owner_client, team_id)

        create = owner_client.post(
            "/api/v1/reports",
            json={"projectId": project["id"], "title": "Weekly summary"},
        )
        assert create.status_code == 200
        rid = create.json()["id"]
        assert create.json()["title"] == "Weekly summary"
        assert create.json()["content"]["type"] == "doc"

        listed = owner_client.get(f"/api/v1/projects/{project['id']}/reports")
        assert listed.status_code == 200
        assert listed.json()["data"][0]["id"] == rid

        got = owner_client.get(f"/api/v1/reports/{rid}")
        assert got.status_code == 200

        patched = owner_client.patch(
            f"/api/v1/reports/{rid}",
            json={
                "title": "Weekly summary v2",
                "content": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Hello"}],
                        }
                    ],
                },
            },
        )
        assert patched.status_code == 200
        assert patched.json()["title"] == "Weekly summary v2"
        assert patched.json()["content"]["content"][0]["content"][0]["text"] == "Hello"

        member_client = auth_client(test_user_2)
        member_list = member_client.get(f"/api/v1/projects/{project['id']}/reports")
        assert member_list.status_code == 200

    async def test_viewer_cannot_create_report(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="viewer")
        project = _create_project(owner_client, team_id)

        viewer_client = auth_client(test_user_2)
        response = viewer_client.post(
            "/api/v1/reports",
            json={"projectId": project["id"], "title": "Nope"},
        )
        assert response.status_code == 403
