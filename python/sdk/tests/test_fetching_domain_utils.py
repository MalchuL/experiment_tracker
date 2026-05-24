from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.domain.experiments.dto import (
    ExperimentListResponse,
    ExperimentResponse,
)
from experiment_tracker_sdk.client.domain.projects.dto import (
    ProjectListResponse,
    ProjectResponse,
)
from experiment_tracker_sdk.client.domain.teams.dto import (
    TeamListItemResponse,
    TeamListResponse,
)
from experiment_tracker_sdk.client.request_types import ApiRequestSpec
from experiment_tracker_sdk.client.fetching_domain_pages import (
    fetch_all_project_experiments,
    fetch_all_projects,
    fetch_all_teams,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def request(self, spec: ApiRequestSpec[Any]) -> Any:
        query_params = spec.query_params or {}
        self.calls.append((spec.endpoint, query_params))
        offset = int(query_params.get("offset", 0))

        if spec.endpoint == "/projects":
            if offset == 0:
                return ProjectListResponse(
                    data=[_project("project-1")],
                    hasNext=True,
                    size=1,
                    total=2,
                )
            return ProjectListResponse(
                data=[_project("project-2")],
                hasNext=False,
                size=1,
                total=2,
            )

        if spec.endpoint == "/projects/project-1/experiments":
            if offset == 0:
                return ExperimentListResponse(
                    data=[_experiment("experiment-1")],
                    hasNext=True,
                    size=1,
                    total=2,
                )
            return ExperimentListResponse(
                data=[_experiment("experiment-2")],
                hasNext=False,
                size=1,
                total=2,
            )

        if spec.endpoint == "/teams":
            if offset == 0:
                return TeamListResponse(
                    data=[_team("team-1")],
                    hasNext=True,
                    size=1,
                    total=2,
                )
            return TeamListResponse(
                data=[_team("team-2")],
                hasNext=False,
                size=1,
                total=2,
            )

        raise AssertionError(f"Unexpected endpoint: {spec.endpoint}")


def _project(project_id: str) -> ProjectResponse:
    return ProjectResponse(
        id=project_id,
        name=project_id,
        description="",
        metrics={},
        settings=[],
        owner={"id": "user-1"},
        createdAt=datetime(2026, 1, 1),
    )


def _experiment(experiment_id: str) -> ExperimentResponse:
    return ExperimentResponse(
        id=experiment_id,
        projectId="project-1",
        name=experiment_id,
        description="",
        status="planned",
        createdAt=datetime(2026, 1, 1),
    )


def _team(team_id: str) -> TeamListItemResponse:
    return TeamListItemResponse(
        id=team_id,
        createdAt=datetime(2026, 1, 1),
        ownerId="user-1",
        name=team_id,
        canCreateProject=True,
    )


def test_fetch_all_projects_uses_paginated_project_endpoint() -> None:
    client = FakeClient()
    projects = fetch_all_projects(
        limit=1,
        request_client=cast(ExperimentTrackerClient, client),
        api_requests_registry=APIRequestsRegistry(),
    )

    assert [project.id for project in projects] == ["project-1", "project-2"]
    assert client.calls == [
        ("/projects", {"limit": 1, "offset": 0}),
        ("/projects", {"limit": 1, "offset": 1}),
    ]


def test_fetch_all_project_experiments_uses_paginated_project_endpoint() -> None:
    client = FakeClient()
    experiments = fetch_all_project_experiments(
        "project-1",
        search="run",
        include_features=False,
        limit=1,
        request_client=cast(ExperimentTrackerClient, client),
        api_requests_registry=APIRequestsRegistry(),
    )

    assert [experiment.id for experiment in experiments] == [
        "experiment-1",
        "experiment-2",
    ]
    assert client.calls == [
        (
            "/projects/project-1/experiments",
            {
                "limit": 1,
                "offset": 0,
                "search": "run",
                "includeFeatures": "false",
            },
        ),
        (
            "/projects/project-1/experiments",
            {
                "limit": 1,
                "offset": 1,
                "search": "run",
                "includeFeatures": "false",
            },
        ),
    ]


def test_fetch_all_teams_uses_paginated_team_endpoint() -> None:
    client = FakeClient()
    teams = fetch_all_teams(
        limit=1,
        request_client=cast(ExperimentTrackerClient, client),
        api_requests_registry=APIRequestsRegistry(),
    )

    assert [team.id for team in teams] == ["team-1", "team-2"]
    assert client.calls == [
        ("/teams", {"limit": 1, "offset": 0}),
        ("/teams", {"limit": 1, "offset": 1}),
    ]
