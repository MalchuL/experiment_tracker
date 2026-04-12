from typing import Any, Callable, cast
from uuid import UUID

from .dto import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMetricsResponse,
    ProjectResponse,
    ProjectSettingResponse,
    ProjectUpdateRequest,
    SuccessResponse,
)
from ...request import ApiRequestSpec


class ProjectRequestSpecFactory:
    ENDPOINTS = {
        "get_all_projects": "/projects",
        "create_project": "/projects",
        "get_project": lambda project_id: f"/projects/{project_id}",
        "update_project": lambda project_id: f"/projects/{project_id}",
        "delete_project": lambda project_id: f"/projects/{project_id}",
    }

    def get_all_projects(self) -> ApiRequestSpec[ProjectListResponse]:
        endpoint = cast(str, self.ENDPOINTS["get_all_projects"])
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=ProjectListResponse,
        )

    def get_project(self, project_id: str | UUID) -> ApiRequestSpec[ProjectResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_project"])(project_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=ProjectResponse,
        )

    def create_project(
        self,
        name: str,
        description: str = "",
        metrics: ProjectMetricsResponse | None = None,
        settings: list[ProjectSettingResponse] | None = None,
        team_id: str | None = None,
    ) -> ApiRequestSpec[ProjectResponse]:
        endpoint = cast(str, self.ENDPOINTS["create_project"])
        payload = ProjectCreateRequest(
            name=name,
            description=description,
            metrics=metrics or ProjectMetricsResponse(),
            settings=settings or [],
            teamId=team_id,
        )
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=ProjectResponse,
        )

    def update_project(
        self,
        project_id: str | UUID,
        name: str | None = None,
        description: str | None = None,
        metrics: ProjectMetricsResponse | None = None,
        settings: list[ProjectSettingResponse] | None = None,
    ) -> ApiRequestSpec[ProjectResponse]:
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
        return ApiRequestSpec(
            method="PATCH",
            endpoint=endpoint,
            request_payload=payload,
            response_model=ProjectResponse,
        )

    def delete_project(self, project_id: str | UUID) -> ApiRequestSpec[SuccessResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["delete_project"])(
            project_id
        )
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=SuccessResponse,
        )


# Backward-compatible alias.
ProjectService = ProjectRequestSpecFactory
