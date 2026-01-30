from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import current_active_user
from db.database import get_async_session
from domain.api_tokens.controller import router as api_tokens_router
from domain.projects.controller import router as projects_router
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from models import Project, Role, User


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_tokens_router)
    app.include_router(projects_router, prefix="/api")
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


@pytest.mark.asyncio
async def test_create_and_list_tokens(
    client: TestClient, db_session: AsyncSession, test_user: User
):
    response = client.post(
        "/users/me/api-tokens",
        json={
            "name": "Test token",
            "description": "token for tests",
            "scopes": [ProjectActions.VIEW_PROJECT],
        },
    )
    assert response.status_code == 200
    created = response.json()
    assert created["token"].startswith("pat_")
    assert created["name"] == "Test token"

    list_response = client.get("/users/me/api-tokens")
    assert list_response.status_code == 200
    tokens = list_response.json()
    assert len(tokens) == 1
    assert tokens[0]["name"] == "Test token"
    assert "token" not in tokens[0]


@pytest.mark.asyncio
async def test_update_token_returns_list_item_dto(
    client: TestClient, db_session: AsyncSession, test_user: User
):
    create_response = client.post(
        "/users/me/api-tokens",
        json={
            "name": "Update token",
            "description": "before update",
            "scopes": [ProjectActions.VIEW_PROJECT],
        },
    )
    assert create_response.status_code == 200
    token_id = create_response.json()["id"]

    update_response = client.patch(
        f"/users/me/api-tokens/{token_id}",
        json={
            "name": "Updated token",
            "description": "after update",
            "scopes": [ProjectActions.EDIT_PROJECT],
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == token_id
    assert updated["name"] == "Updated token"
    assert updated["description"] == "after update"
    assert updated["scopes"] == [ProjectActions.EDIT_PROJECT]
    assert "token" not in updated


@pytest.mark.asyncio
async def test_list_tokens_returns_list_item_dto_fields(
    client: TestClient, db_session: AsyncSession, test_user: User
):
    create_response = client.post(
        "/users/me/api-tokens",
        json={
            "name": "List token",
            "description": "list token",
            "scopes": [ProjectActions.VIEW_PROJECT],
        },
    )
    assert create_response.status_code == 200

    list_response = client.get("/users/me/api-tokens")
    assert list_response.status_code == 200
    token = list_response.json()[0]
    assert token["name"] == "List token"
    assert token["description"] == "list token"
    assert token["scopes"] == [ProjectActions.VIEW_PROJECT]
    assert "token" not in token


@pytest.mark.asyncio
async def test_pat_auth_access_projects(
    client: TestClient, db_session: AsyncSession, test_user: User
):
    project = Project(
        id=uuid4(),
        name="Test Project",
        description="",
        owner_id=test_user.id,
        team_id=None,
    )
    db_session.add(project)
    await db_session.flush()

    permission_service = PermissionService(db_session)
    await permission_service.add_user_to_project_permissions(
        test_user.id, project.id, Role.ADMIN
    )

    token_response = client.post(
        "/users/me/api-tokens",
        json={
            "name": "Access token",
            "scopes": [ProjectActions.VIEW_PROJECT],
        },
    )
    raw_token = token_response.json()["token"]

    projects_response = client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert projects_response.status_code == 200


@pytest.mark.asyncio
async def test_revoked_token_denied(
    client: TestClient, db_session: AsyncSession, test_user: User
):
    project = Project(
        id=uuid4(),
        name="Test Project",
        description="",
        owner_id=test_user.id,
        team_id=None,
    )
    db_session.add(project)
    await db_session.flush()
    permission_service = PermissionService(db_session)
    await permission_service.add_user_to_project_permissions(
        test_user.id, project.id, Role.ADMIN
    )

    token_response = client.post(
        "/users/me/api-tokens",
        json={
            "name": "Revocable token",
            "scopes": [ProjectActions.VIEW_PROJECT],
        },
    )
    raw_token = token_response.json()["token"]
    token_id = token_response.json()["id"]

    revoke_response = client.delete(f"/users/me/api-tokens/{token_id}")
    assert revoke_response.status_code == 200

    projects_response = client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert projects_response.status_code == 401
