from typing import Any, Callable, Optional, cast
from uuid import UUID

from .dto import (
    ExperimentCreateRequest,
    ExperimentListResponse,
    ExperimentResponse,
    ExperimentStatus,
    SuccessResponse,
    ExperimentUpdateRequest,
)
from .limits import truncate_experiment_description, truncate_experiment_name
from ...constants import UNSET, Unset
from ...request_types import ApiRequestSpec


class ExperimentRequestSpecFactory:
    ENDPOINTS = {
        "create_experiment": "/experiments",
        "get_recent_experiments": "/experiments/recent",
        "update_experiment": lambda experiment_id: f"/experiments/{experiment_id}",
        "get_experiment": lambda experiment_id: f"/experiments/{experiment_id}",
        "delete_experiment": lambda experiment_id: f"/experiments/{experiment_id}",
        "get_experiments_by_project": lambda project_id: f"/projects/{project_id}/experiments",
    }

    def create_experiment(
        self,
        project_id: str | UUID,
        name: str,
        description: str = "",
        color: Optional[str | Unset] = UNSET,
        parent_experiment_id: Optional[str | UUID | Unset] = UNSET,
        features: Optional[dict[str, Any] | Unset] = UNSET,
        status: ExperimentStatus = ExperimentStatus.PLANNED,
        tags: Optional[list[str] | Unset] = UNSET,
    ) -> ApiRequestSpec[ExperimentResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint: str = cast(str, self.ENDPOINTS["create_experiment"])
        t_name = truncate_experiment_name(name)
        t_description = truncate_experiment_description(description)
        kwargs: dict[str, Any] = {}
        if color is not UNSET:
            kwargs["color"] = color
        if parent_experiment_id is not UNSET:
            kwargs["parentExperimentId"] = parent_experiment_id
        if features is not UNSET:
            kwargs["features"] = features
        if tags is not UNSET:
            kwargs["tags"] = tags
        payload = ExperimentCreateRequest(
            projectId=project_id,
            name=t_name,
            description=t_description,
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
        if not isinstance(name, Unset):
            kwargs["name"] = None if name is None else truncate_experiment_name(name)
        if not isinstance(description, Unset):
            kwargs["description"] = (
                None
                if description is None
                else truncate_experiment_description(description)
            )
        if color is not UNSET:
            kwargs["color"] = color
        if parent_experiment_id is not UNSET:
            kwargs["parentExperimentId"] = parent_experiment_id
        if features is not UNSET:
            kwargs["features"] = features
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

    def get_experiment(
        self, experiment_id: str | UUID
    ) -> ApiRequestSpec[ExperimentResponse]:
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
        self,
        project_id: str | UUID,
        limit: int | None = None,
        offset: int | None = None,
        search: str | None = None,
    ) -> ApiRequestSpec[ExperimentListResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint: str = cast(
            Callable[[Any], str], self.ENDPOINTS["get_experiments_by_project"]
        )(project_id)
        query_params: dict[str, str | int] = {}
        if limit is not None:
            query_params["limit"] = limit
        if offset is not None:
            query_params["offset"] = offset
        if search is not None and search.strip() != "":
            query_params["search"] = search.strip()
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=ExperimentListResponse,
            query_params=query_params or None,
        )

    def get_recent_experiments(
        self,
        project_id: str | UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[ExperimentListResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint: str = cast(str, self.ENDPOINTS["get_recent_experiments"])
        query_params: dict[str, str | int] = {"projectId": project_id}
        if limit is not None:
            query_params["limit"] = limit
        if offset is not None:
            query_params["offset"] = offset
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=ExperimentListResponse,
            query_params=query_params,
        )

    def delete_experiment(
        self, experiment_id: str | UUID
    ) -> ApiRequestSpec[SuccessResponse]:
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
