from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from ...request_types import ApiRequestSpec
from .dto import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMetricsResponse,
    ProjectResponse,
    ProjectSettingResponse,
    ProjectUpdateRequest,
    SuccessResponse,
)
from .limits import truncate_project_description, truncate_project_name


class ProjectRequestSpecFactory:
    ENDPOINTS = {
        "get_all_projects": "/projects",
        "create_project": "/projects",
        "get_project": lambda project_id: f"/projects/{project_id}",
        "get_project_settings_map": (
            lambda project_id: f"/projects/{project_id}/settings/map"
        ),
        "update_project": lambda project_id: f"/projects/{project_id}",
        "delete_project": lambda project_id: f"/projects/{project_id}",
    }

    def get_all_projects(
        self,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[ProjectListResponse]:
        endpoint = cast(str, self.ENDPOINTS["get_all_projects"])
        query_params: dict[str, int] = {}
        if limit is not None:
            query_params["limit"] = limit
        if offset is not None:
            query_params["offset"] = offset
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=ProjectListResponse,
            query_params=query_params or None,
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

    def get_project_settings_map(
        self, project_id: str | UUID
    ) -> ApiRequestSpec[Any]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(
            Callable[[Any], str],
            self.ENDPOINTS["get_project_settings_map"],
        )
        endpoint = endpoint(project_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
        )

    def create_project(
        self,
        name: str,
        description: str = "",
        metrics: ProjectMetricsResponse | None = None,
        settings: list[ProjectSettingResponse] | None = None,
        team_id: str | UUID | None = None,
    ) -> ApiRequestSpec[ProjectResponse]:
        endpoint = cast(str, self.ENDPOINTS["create_project"])
        payload = ProjectCreateRequest(
            name=truncate_project_name(name),
            description=truncate_project_description(description),
            metrics=metrics or ProjectMetricsResponse(),
            settings=settings or [],
            teamId=None if team_id is None else str(team_id),
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
        payload_kwargs: dict[str, Any] = {}
        if name is not None:
            payload_kwargs["name"] = truncate_project_name(name)
        if description is not None:
            payload_kwargs["description"] = truncate_project_description(description)
        if metrics is not None:
            payload_kwargs["metrics"] = metrics
        if settings is not None:
            payload_kwargs["settings"] = settings
        payload = ProjectUpdateRequest(**payload_kwargs)
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
