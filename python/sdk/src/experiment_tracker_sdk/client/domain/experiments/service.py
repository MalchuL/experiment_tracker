from typing import Any, Callable, Optional, cast
from uuid import UUID

from .dto import (
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentStatus,
    SuccessResponse,
    ExperimentUpdateRequest,
)
from ...constants import UNSET, Unset
from ...request import ApiRequestSpec


class ExperimentRequestSpecFactory:
    ENDPOINTS = {
        "create_experiment": "/api/experiments",
        "get_recent_experiments": "/api/experiments/recent",
        "update_experiment": lambda experiment_id: f"/api/experiments/{experiment_id}",
        "get_experiment": lambda experiment_id: f"/api/experiments/{experiment_id}",
        "delete_experiment": lambda experiment_id: f"/api/experiments/{experiment_id}",
        "get_experiments_by_project": lambda project_id: f"/api/projects/{project_id}/experiments",
    }

    def create_experiment(
        self,
        project_id: str | UUID,
        name: str,
        description: str = "",
        color: Optional[str | Unset] = UNSET,
        parent_experiment_id: Optional[str | UUID | Unset] = UNSET,
        features: Optional[dict[str, Any] | Unset] = UNSET,
        git_diff: Optional[str | Unset] = UNSET,
        status: ExperimentStatus = ExperimentStatus.PLANNED,
        tags: Optional[list[str] | Unset] = UNSET,
    ) -> ApiRequestSpec[ExperimentResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint: str = cast(str, self.ENDPOINTS["create_experiment"])
        kwargs: dict[str, Any] = {}
        if color is not UNSET:
            kwargs["color"] = color
        if parent_experiment_id is not UNSET:
            kwargs["parentExperimentId"] = parent_experiment_id
        if features is not UNSET:
            kwargs["features"] = features
        if git_diff is not UNSET:
            kwargs["gitDiff"] = git_diff
        if tags is not UNSET:
            kwargs["tags"] = tags
        payload = ExperimentCreateRequest(
            projectId=project_id,
            name=name,
            description=description,
            status=status,
            **kwargs,
        )
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=ExperimentResponse,
        )

    def update_experiment(
        self,
        experiment_id: str | UUID,
        name: Optional[str | Unset] = UNSET,
        description: Optional[str | Unset] = UNSET,
        color: Optional[str | Unset] = UNSET,
        parent_experiment_id: Optional[str | UUID | Unset] = UNSET,
        features: Optional[dict[str, Any] | Unset] = UNSET,
        git_diff: Optional[str | Unset] = UNSET,
        status: Optional[ExperimentStatus | Unset] = UNSET,
        progress: Optional[int | Unset] = UNSET,
        tags: Optional[list[str] | Unset] = UNSET,
    ) -> ApiRequestSpec[ExperimentResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint: str = cast(Callable[[Any], str], self.ENDPOINTS["update_experiment"])(
            experiment_id
        )
        kwargs: dict[str, Any] = {}
        if name is not UNSET:
            kwargs["name"] = name
        if description is not UNSET:
            kwargs["description"] = description
        if color is not UNSET:
            kwargs["color"] = color
        if parent_experiment_id is not UNSET:
            kwargs["parentExperimentId"] = parent_experiment_id
        if features is not UNSET:
            kwargs["features"] = features
        if git_diff is not UNSET:
            kwargs["gitDiff"] = git_diff
        if status is not UNSET:
            kwargs["status"] = status
        if progress is not UNSET:
            kwargs["progress"] = progress
        if tags is not UNSET:
            kwargs["tags"] = tags
        payload = ExperimentUpdateRequest(**kwargs)
        return ApiRequestSpec(
            method="PATCH",
            endpoint=endpoint,
            request_payload=payload,
            response_model=ExperimentResponse,
        )

    def get_experiment(self, experiment_id: str | UUID) -> ApiRequestSpec[ExperimentResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint: str = cast(Callable[[Any], str], self.ENDPOINTS["get_experiment"])(
            experiment_id
        )
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=ExperimentResponse,
        )

    def get_experiments_by_project(
        self, project_id: str | UUID
    ) -> ApiRequestSpec[ExperimentResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint: str = cast(
            Callable[[Any], str], self.ENDPOINTS["get_experiments_by_project"]
        )(project_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=ExperimentResponse,
            response_is_list=True,
        )

    def delete_experiment(self, experiment_id: str | UUID) -> ApiRequestSpec[SuccessResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint: str = cast(Callable[[Any], str], self.ENDPOINTS["delete_experiment"])(
            experiment_id
        )
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=SuccessResponse,
        )


# Backward-compatible alias.
ExperimentService = ExperimentRequestSpecFactory
