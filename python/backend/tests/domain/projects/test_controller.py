"""
Tests for the project controller (API endpoints).

These tests use FastAPI TestClient to test the HTTP layer and permissions
for standalone and team-scoped projects.
"""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual
from db.database import get_async_session
from domain.projects.controller import router as projects_router
from api.routes.service_dependencies import get_scalars_service
from domain.scalars.service import NoOpScalarsService
from domain.team.teams.controller import router as teams_router
from models import User


def create_test_app() -> FastAPI:
    """Create a test FastAPI app with project and team routers."""
    app = FastAPI()
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(teams_router, prefix="/api/v1")
    return app


@pytest.fixture
def test_app(db_session: AsyncSession, test_user: User) -> FastAPI:
    """Create a test app with dependency overrides."""
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
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_client(test_app: FastAPI):
    """
    Create a test client with configurable authentication.

    Returns a function that accepts a user and returns a client authenticated as that user.
    """

    def _get_auth_client(user: User) -> TestClient:
        async def override_current_user():
            return user

        test_app.dependency_overrides[get_current_user_dual] = override_current_user
        return TestClient(test_app)

    return _get_auth_client


def _create_team(client: TestClient, name: str = "Test Team") -> str:
    response = client.post(
        "/api/v1/teams",
        json={"name": name, "description": "Team for project tests"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def _add_team_member(
    client: TestClient, team_id: str, user_id: str, role: str = "member"
) -> None:
    response = client.post(
        "/api/v1/teams/members",
        json={"userId": user_id, "teamId": team_id, "role": role},
    )
    assert response.status_code == 200


def _create_project(client: TestClient, name: str, team_id: str | None = None) -> dict:
    payload = {"name": name, "description": "Project for tests"}
    if team_id:
        payload["teamId"] = team_id
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 200
    return response.json()


class TestProjectControllerCreate:
    async def test_create_project_without_team(
        self, client: TestClient, test_user: User
    ):
        response = client.post(
            "/api/v1/projects",
            json={"name": "Standalone Project", "description": "No team"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Standalone Project"
        assert data["description"] == "No team"
        assert data["team"] is None
        assert data["owner"]["id"] == str(test_user.id)
        assert data["experimentCount"] == 0
        assert data["hypothesisCount"] == 0
        assert "createdAt" in data

    async def test_create_project_in_team_as_admin(self, auth_client, test_user: User):
        client1 = auth_client(test_user)
        team_id = _create_team(client1, name="Admin Team")

        response = client1.post(
            "/api/v1/projects",
            json={
                "name": "Team Project",
                "description": "Team scoped",
                "teamId": team_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Team Project"
        assert data["team"]["id"] == team_id
        assert data["owner"]["id"] == str(test_user.id)

    async def test_create_project_in_team_denied_for_member(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        team_id = _create_team(client1, name="Member Team")
        _add_team_member(client1, team_id, str(test_user_2.id), role="member")

        client2 = auth_client(test_user_2)
        response = client2.post(
            "/api/v1/projects",
            json={
                "name": "Denied Project",
                "description": "Should not be created",
                "teamId": team_id,
            },
        )

        assert response.status_code == 404
        assert "not allowed" in response.json()["detail"].lower()


class TestProjectControllerRead:
    async def test_get_project_accessible_for_team_member(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        team_id = _create_team(client1, name="Viewer Team")
        _add_team_member(client1, team_id, str(test_user_2.id), role="viewer")
        project = _create_project(client1, name="Viewer Project", team_id=team_id)

        client2 = auth_client(test_user_2)
        response = client2.get(f"/api/v1/projects/{project['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == project["id"]

    async def test_get_project_denied_for_non_member(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        project = _create_project(client1, name="Private Project")

        client2 = auth_client(test_user_2)
        response = client2.get(f"/api/v1/projects/{project['id']}")

        assert response.status_code == 404

    async def test_list_projects_scoped_to_access(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        team_id = _create_team(client1, name="Access Team")
        _add_team_member(client1, team_id, str(test_user_2.id), role="viewer")

        team_project = _create_project(client1, name="Team Project", team_id=team_id)
        standalone_project = _create_project(client1, name="Standalone Project")

        client2 = auth_client(test_user_2)
        response = client2.get("/api/v1/projects")

        assert response.status_code == 200
        payload = response.json()
        assert payload["size"] == 1
        assert payload["hasNext"] is False
        project_ids = {item["id"] for item in payload["data"]}
        assert project_ids == {team_project["id"]}

        client1 = auth_client(test_user)
        response_owner = client1.get("/api/v1/projects")
        assert response_owner.status_code == 200
        owner_payload = response_owner.json()
        assert owner_payload["size"] == 2
        assert owner_payload["hasNext"] is False
        owner_ids = {item["id"] for item in owner_payload["data"]}
        assert owner_ids == {team_project["id"], standalone_project["id"]}


class TestProjectControllerUpdate:
    async def test_update_project_as_admin(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        team_id = _create_team(client1, name="Admin Update Team")
        _add_team_member(client1, team_id, str(test_user_2.id), role="admin")
        project = _create_project(client1, name="Update Target", team_id=team_id)

        client2 = auth_client(test_user_2)
        response = client2.patch(
            f"/api/v1/projects/{project['id']}",
            json={"name": "Updated Project"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Project"

    async def test_update_project_denied_without_permission(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        project = _create_project(client1, name="Locked Project")

        client2 = auth_client(test_user_2)
        response = client2.patch(
            f"/api/v1/projects/{project['id']}",
            json={"name": "Hacked Project"},
        )

        assert response.status_code == 403


class TestProjectControllerDelete:
    async def test_delete_project_as_admin(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        team_id = _create_team(client1, name="Delete Team")
        _add_team_member(client1, team_id, str(test_user_2.id), role="admin")
        project = _create_project(client1, name="Deletable Project", team_id=team_id)

        client2 = auth_client(test_user_2)
        response = client2.delete(f"/api/v1/projects/{project['id']}?detailed=true")

        assert response.status_code == 200
        body = response.json()
        print(body)
        assert body["partial"] is False
        # one error for the project table deletion inside object storage
        assert len(body["errors"]) == 0
        assert any(r["category"] == "postgres:project" for r in body["results"])

    async def test_delete_project_denied_without_permission(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        project = _create_project(client1, name="Protected Project")

        client2 = auth_client(test_user_2)
        response = client2.delete(f"/api/v1/projects/{project['id']}")

        assert response.status_code == 403


class TestProjectControllerSettings:
    async def test_settings_crud_flow(self, client: TestClient):
        project = _create_project(client, name="Settings Project")

        add_response = client.post(
            f"/api/v1/projects/{project['id']}/settings",
            json={
                "name": "maxEpochs",
                "description": "",
                "type": "int",
                "value": 10,
            },
        )
        assert add_response.status_code == 200
        settings = add_response.json()
        assert len(settings) == 1
        assert settings[0]["name"] == "maxEpochs"
        assert settings[0]["value"] == 10

        get_response = client.get(f"/api/v1/projects/{project['id']}/settings")
        assert get_response.status_code == 200
        assert get_response.json()[0]["name"] == "maxEpochs"

        map_response = client.get(f"/api/v1/projects/{project['id']}/settings/map")
        assert map_response.status_code == 200
        assert map_response.json() == {"maxEpochs": 10}

        update_response = client.patch(
            f"/api/v1/projects/{project['id']}/settings/maxEpochs",
            json={"value": 20},
        )
        assert update_response.status_code == 200
        assert update_response.json()["value"] == 20

        delete_response = client.delete(
            f"/api/v1/projects/{project['id']}/settings/maxEpochs"
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

    async def test_settings_update_validates_type(self, client: TestClient):
        project = _create_project(client, name="Settings Type Validation")
        add_response = client.post(
            f"/api/v1/projects/{project['id']}/settings",
            json={
                "name": "isEnabled",
                "description": "",
                "type": "boolean",
                "value": True,
            },
        )
        assert add_response.status_code == 200

        invalid_update = client.patch(
            f"/api/v1/projects/{project['id']}/settings/isEnabled",
            json={"value": "yes"},
        )
        assert invalid_update.status_code == 400
