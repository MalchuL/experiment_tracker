"""Tests for admin panel routes and change-password."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import create_app
from api.routes.auth import get_current_user_dual
from db.database import get_async_session
from models import User


@pytest.fixture
async def app(db_session: AsyncSession, test_user: User) -> FastAPI:
    ph = PasswordHelper()
    test_user.hashed_password = ph.hash("testpassword")
    await db_session.flush()

    application = create_app()

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return test_user

    application.dependency_overrides[get_async_session] = override_get_db
    application.dependency_overrides[get_current_user_dual] = override_current_user
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestAdminRoutes:
    def test_admin_users_requires_header(self, client: TestClient):
        r = client.get("/api/admin/users")
        assert r.status_code == 403

    def test_admin_users_wrong_key(self, client: TestClient):
        r = client.get("/api/admin/users", headers={"X-Admin-Key": "wrong"})
        assert r.status_code == 403

    def test_admin_users_search_by_uuid_substring(self, client: TestClient, test_user: User):
        uid = str(test_user.id)
        fragment = uid.split("-")[0]
        r = client.get(
            f"/api/admin/users?q={fragment}",
            headers={"X-Admin-Key": "admin"},
        )
        assert r.status_code == 200
        ids = {row["id"] for row in r.json()}
        assert str(test_user.id) in ids

    def test_admin_reset_password(self, client: TestClient, test_user_2: User):
        r = client.post(
            f"/api/admin/users/{test_user_2.id}/reset-password",
            headers={"X-Admin-Key": "admin"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["userId"] == str(test_user_2.id)
        assert body["email"] == test_user_2.email
        assert len(body["temporaryPassword"]) >= 12

    def test_admin_teams(self, client: TestClient):
        r = client.get("/api/admin/teams", headers={"X-Admin-Key": "admin"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestChangePassword:
    def test_change_password_wrong_current(self, client: TestClient):
        r = client.post(
            "/api/users/me/change-password",
            json={"currentPassword": "not-the-password", "newPassword": "newpass123"},
        )
        assert r.status_code == 400

    def test_change_password_success(self, client: TestClient, test_user: User):
        r = client.post(
            "/api/users/me/change-password",
            json={"currentPassword": "testpassword", "newPassword": "newpass123"},
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"success": True}

        login = client.post(
            "/api/auth/jwt/login",
            data={"username": test_user.email, "password": "newpass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login.status_code == 200, login.text

        client.post(
            "/api/users/me/change-password",
            json={"currentPassword": "newpass123", "newPassword": "testpassword"},
        )
