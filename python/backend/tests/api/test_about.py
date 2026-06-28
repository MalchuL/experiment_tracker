"""Tests for ``GET /about``."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.about_dto import ABOUT_DESCRIPTION, get_backend_version
from api.main import create_app
from config.settings import get_settings
from db.database import get_async_session


@pytest.fixture
async def app(db_session: AsyncSession) -> FastAPI:
    application = create_app()

    async def override_get_db():
        yield db_session

    application.dependency_overrides[get_async_session] = override_get_db
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_about_returns_metadata(client: TestClient) -> None:
    response = client.get("/api/about")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == get_settings().app_name
    assert body["version"] == get_backend_version()
    assert body["description"] == ABOUT_DESCRIPTION
