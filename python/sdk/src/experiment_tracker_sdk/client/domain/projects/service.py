from typing import Any, Callable, cast
from uuid import UUID

from .dto import (
    ProjectCreateRequest,
    ProjectMetricResponse,
    ProjectResponse,
    ProjectSettingsResponse,
    ProjectUpdateRequest,
    SuccessResponse,
)
from ...client import ExperimentTrackerClient


class ProjectService:
    ENDPOINTS = {
        "get_all_projects": "/api/projects",
        "create_project": "/api/projects",
        "get_project": lambda project_id: f"/api/projects/{project_id}",
        "update_project": lambda project_id: f"/api/projects/{project_id}",
        "delete_project": lambda project_id: f"/api/projects/{project_id}",
    }

    def __init__(self, client: ExperimentTrackerClient):
        self._client = client

    def get_all_projects(self) -> list[ProjectResponse]:
        endpoint = cast(str, self.ENDPOINTS["get_all_projects"])
        response = self._client.request("GET", endpoint)
        return [ProjectResponse.model_validate(item) for item in response.json()]

    def get_project(self, project_id: str | UUID) -> ProjectResponse:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_project"])(project_id)
        response = self._client.request("GET", endpoint)
        return ProjectResponse.model_validate(response.json())

    def create_project(
        self,
        name: str,
        description: str = "",
        metrics: list[ProjectMetricResponse] | None = None,
        settings: ProjectSettingsResponse | None = None,
        team_id: str | None = None,
    ) -> ProjectResponse:
        endpoint = cast(str, self.ENDPOINTS["create_project"])
        payload = ProjectCreateRequest(
            name=name,
            description=description,
            metrics=metrics or [],
            settings=settings,
            teamId=team_id,
        )
        response = self._client.request("POST", endpoint, json=payload)
        return ProjectResponse.model_validate(response.json())

    def update_project(
        self,
        project_id: str | UUID,
        name: str | None = None,
        description: str | None = None,
        metrics: list[ProjectMetricResponse] | None = None,
        settings: ProjectSettingsResponse | None = None,
    ) -> ProjectResponse:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["update_project"])(
            project_id
        )
        payload = ProjectUpdateRequest(
            name=name,
            description=description,
            metrics=metrics,
            settings=settings,
        )
        response = self._client.request("PATCH", endpoint, json=payload)
        return ProjectResponse.model_validate(response.json())

    def delete_project(self, project_id: str | UUID) -> SuccessResponse:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["delete_project"])(
            project_id
        )
        response = self._client.request("DELETE", endpoint)
        return SuccessResponse.model_validate(response.json())
