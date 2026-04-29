"""HTTP tests for project members endpoints."""

import uuid

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
    app = FastAPI()
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(teams_router, prefix="/api/v1")
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


class TestProjectMembersController:
    async def test_list_members_includes_owner(
        self, client: TestClient, db_session: AsyncSession, test_user: User
    ):
        create = client.post(
            "/api/v1/projects",
            json={"name": "Member List", "description": ""},
        )
        assert create.status_code == 200
        pid = create.json()["id"]

        r = client.get(f"/api/v1/projects/{pid}/members")
        assert r.status_code == 200
        members = r.json()
        assert len(members) >= 1
        owner_row = next(m for m in members if m["userId"] == str(test_user.id))
        assert owner_row["accessSource"] == "direct"

    async def test_invite_and_remove_member(
        self,
        auth_client,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        client1 = auth_client(test_user)
        create = client1.post(
            "/api/v1/projects",
            json={"name": "Invite Flow", "description": ""},
        )
        pid = create.json()["id"]

        inv = client1.post(
            f"/api/v1/projects/{pid}/members",
            json={"email": test_user_2.email, "role": "viewer"},
        )
        assert inv.status_code == 200
        assert inv.json()["userId"] == str(test_user_2.id)

        lookup = client1.get(
            f"/api/v1/projects/{pid}/users/lookup",
            params={"email": test_user_2.email},
        )
        assert lookup.status_code == 200
        assert lookup.json()["id"] == str(test_user_2.id)

        rem = client1.request(
            "DELETE",
            f"/api/v1/projects/{pid}/members",
            json={"userId": str(test_user_2.id)},
        )
        assert rem.status_code == 200

    async def test_cannot_remove_owner(
        self, auth_client, test_user: User, test_user_2: User
    ):
        client1 = auth_client(test_user)
        create = client1.post(
            "/api/v1/projects",
            json={"name": "Owner Guard", "description": ""},
        )
        pid = create.json()["id"]

        rem = client1.request(
            "DELETE",
            f"/api/v1/projects/{pid}/members",
            json={"userId": str(test_user.id)},
        )
        assert rem.status_code == 403

    async def test_team_member_project_role_override(
        self,
        auth_client,
        test_user: User,
        test_user_2: User,
    ):
        owner = auth_client(test_user)
        t = owner.post(
            "/api/v1/teams",
            json={"name": "PM Override Team", "description": ""},
        )
        assert t.status_code == 200
        team_id = t.json()["id"]

        add_m = owner.post(
            "/api/v1/teams/members",
            json={
                "userId": str(test_user_2.id),
                "teamId": team_id,
                "role": "member",
            },
        )
        assert add_m.status_code == 200

        p = owner.post(
            "/api/v1/projects",
            json={
                "name": "Team Proj",
                "description": "",
                "teamId": team_id,
            },
        )
        assert p.status_code == 200
        pid = p.json()["id"]

        r_list = owner.get(f"/api/v1/projects/{pid}/members")
        assert r_list.status_code == 200
        members = r_list.json()
        row2 = next(m for m in members if m["userId"] == str(test_user_2.id))
        assert row2["accessSource"] == "team"
        assert row2["canEdit"] is True
        assert row2["canRemove"] is False

        patch = owner.patch(
            f"/api/v1/projects/{pid}/members",
            json={
                "userId": str(test_user_2.id),
                "role": "viewer",
            },
        )
        assert patch.status_code == 200, patch.text
        body = patch.json()
        assert body["accessSource"] == "override"
        assert body["role"] == "viewer"
        assert body["canRemove"] is True

        r_list2 = owner.get(f"/api/v1/projects/{pid}/members")
        row2b = next(m for m in r_list2.json() if m["userId"] == str(test_user_2.id))
        assert row2b["accessSource"] == "override"

        del_ov = owner.request(
            "DELETE",
            f"/api/v1/projects/{pid}/members",
            json={"userId": str(test_user_2.id)},
        )
        assert del_ov.status_code == 200

        r_list3 = owner.get(f"/api/v1/projects/{pid}/members")
        row2c = next(m for m in r_list3.json() if m["userId"] == str(test_user_2.id))
        assert row2c["accessSource"] == "team"
        assert row2c["role"] == "member"

    async def test_cannot_patch_project_role_for_user_outside_team(
        self, auth_client, test_user: User
    ):
        owner = auth_client(test_user)
        create = owner.post(
            "/api/v1/teams",
            json={"name": "Iso Team", "description": ""},
        )
        assert create.status_code == 200
        team_id = create.json()["id"]
        p = owner.post(
            "/api/v1/projects",
            json={"name": "Iso Proj", "description": "", "teamId": team_id},
        )
        assert p.status_code == 200
        pid = p.json()["id"]

        patch = owner.patch(
            f"/api/v1/projects/{pid}/members",
            json={"userId": str(uuid.uuid4()), "role": "viewer"},
        )
        assert patch.status_code == 403
