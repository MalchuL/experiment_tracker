"""
Tests for the metrics controller (API endpoints).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual
from db.database import get_async_session
from domain.experiments.controller import router as experiments_router
from domain.metrics.controller import router as metrics_router
from domain.metrics.dto import (
    SelectiveMetricsBatchRequestDTO,
    SelectiveTopMetricsRequestDTO,
)
from domain.projects.controller import router as projects_router
from api.routes.service_dependencies import get_scalars_service
from domain.scalars.service import NoOpScalarsService
from domain.team.teams.controller import router as teams_router
from models import User


class TestSelectiveProjectMetricControllerContracts:
    """Validate additive selective project metric route and payload contracts."""

    def test_selective_project_metric_post_routes_are_registered(self) -> None:
        routes = {
            (route.path, method)
            for route in projects_router.routes
            for method in getattr(route, "methods", set())
        }

        assert ("/projects/{project_id}/metrics/batch", "POST") in routes
        assert ("/projects/{project_id}/metrics/top", "POST") in routes

    def test_selective_project_metric_requests_accept_camel_case_payloads(self) -> None:
        batch = SelectiveMetricsBatchRequestDTO.model_validate(
            {
                "experimentIds": ["2c274ad7-9e6a-4dc2-8c75-9d7a1d2b6b55"],
                "metrics": [{"name": "loss", "label": "validation"}],
            }
        )
        top = SelectiveTopMetricsRequestDTO.model_validate(
            {
                "metrics": [
                    {"name": "loss", "label": "", "direction": "minimize"}
                ],
                "k": 3,
            }
        )

        assert batch.metrics[0].label == "validation"
        assert top.metrics[0].label is None
        assert top.metrics[0].direction.value == "minimize"
        assert top.k == 3

    def test_selective_top_metric_request_requires_direction(self) -> None:
        with pytest.raises(ValidationError):
            SelectiveTopMetricsRequestDTO.model_validate(
                {
                    "metrics": [{"name": "loss", "label": "validation"}],
                    "k": 3,
                }
            )


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(teams_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(experiments_router, prefix="/api/v1")
    app.include_router(metrics_router, prefix="/api/v1")
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


def _create_team(client: TestClient, name: str = "Metrics Team") -> str:
    response = client.post(
        "/api/v1/teams",
        json={"name": name, "description": "Team for metrics tests"},
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
            "name": "Metrics Project",
            "description": "Project for metrics",
            "teamId": team_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_experiment(client: TestClient, project_id: str) -> dict:
    response = client.post(
        "/api/v1/experiments",
        json={
            "projectId": project_id,
            "name": "EXP-MET-1",
            "description": "Experiment for metrics",
        },
    )
    assert response.status_code == 200
    return response.json()


class TestMetricControllerUpsert:
    async def test_upsert_metric_as_member(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="member")
        project = _create_project(owner_client, team_id)
        experiment = _create_experiment(owner_client, project["id"])

        member_client = auth_client(test_user_2)
        response = member_client.post(
            "/api/v1/metrics",
            json={
                "experimentId": experiment["id"],
                "name": "accuracy",
                "value": 0.91,
            },
        )

        assert response.status_code == 200
        assert response.json()["experimentId"] == experiment["id"]

    async def test_upsert_metric_member_second_post_updates_value(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="member")
        project = _create_project(owner_client, team_id)
        experiment = _create_experiment(owner_client, project["id"])
        body = {
            "experimentId": experiment["id"],
            "name": "accuracy",
            "value": 0.5,
            "label": "train",
        }
        member_client = auth_client(test_user_2)
        r1 = member_client.post("/api/v1/metrics", json=body)
        assert r1.status_code == 200
        mid = r1.json()["id"]
        r2 = member_client.post(
            "/api/v1/metrics",
            json={**body, "value": 0.9},
        )
        assert r2.status_code == 200
        assert r2.json()["id"] == mid
        assert r2.json()["value"] == 0.9

    async def test_get_metric_by_key_as_member(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="member")
        project = _create_project(owner_client, team_id)
        experiment = _create_experiment(owner_client, project["id"])
        body = {
            "experimentId": experiment["id"],
            "name": "accuracy",
            "value": 0.5,
            "label": "train",
        }
        member_client = auth_client(test_user_2)
        created = member_client.post("/api/v1/metrics", json=body)
        assert created.status_code == 200

        response = member_client.get(
            "/api/v1/metrics/by-key",
            params={
                "experimentId": experiment["id"],
                "name": "accuracy",
                "label": "train",
            },
        )

        assert response.status_code == 200
        assert response.json()["id"] == created.json()["id"]
        assert response.json()["value"] == 0.5

    async def test_upsert_metric_denied_for_viewer(
        self, auth_client, test_user: User, test_user_2: User
    ):
        owner_client = auth_client(test_user)
        team_id = _create_team(owner_client)
        _add_team_member(owner_client, team_id, str(test_user_2.id), role="viewer")
        project = _create_project(owner_client, team_id)
        experiment = _create_experiment(owner_client, project["id"])

        viewer_client = auth_client(test_user_2)
        response = viewer_client.post(
            "/api/v1/metrics",
            json={
                "experimentId": experiment["id"],
                "name": "loss",
                "value": 0.2,
            },
        )

        assert response.status_code == 403

    async def test_upsert_metric_missing_experiment(
        self, auth_client, test_user: User
    ):
        owner_client = auth_client(test_user)
        response = owner_client.post(
            "/api/v1/metrics",
            json={
                "experimentId": "2c274ad7-9e6a-4dc2-8c75-9d7a1d2b6b55",
                "name": "missing",
                "value": 1.0,
            },
        )

        assert response.status_code == 404
