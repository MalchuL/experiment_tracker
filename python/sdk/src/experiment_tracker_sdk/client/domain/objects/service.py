from datetime import datetime
from typing import cast
from uuid import UUID

from .dto import (
    LogObjectRequest,
    LogObjectResponse,
    ObjectsPointsResponse,
)
from ...request import ApiRequestSpec


class ObjectsRequestSpecFactory:
    """Uses artifacts API. Kept as 'objects' for backward compatibility."""

    ENDPOINTS = {
        "log_object": lambda experiment_id: f"/api/experiment-artifacts/{experiment_id}/log_metadata",
        "get_project_objects": lambda project_id: f"/api/project-artifacts/{project_id}/get",
    }

    def log_object(
        self,
        experiment_id: str | UUID,
        request: LogObjectRequest,
    ) -> ApiRequestSpec[LogObjectResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["log_object"](experiment_id))
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=request,
            response_model=LogObjectResponse,
        )

    def get_project_objects(
        self,
        project_id: str | UUID,
        experiment_ids: list[str] | None = None,
        object_types: list[str] | None = None,
        names: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ObjectsPointsResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["get_project_objects"](project_id))
        params: dict[str, object] = {"format": "objects"}
        if experiment_ids:
            params["experiment_id"] = experiment_ids
        if object_types:
            params["artifact_type"] = object_types
        if names:
            params["artifact_name"] = names
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            query_params=params,
            response_model=ObjectsPointsResponse,
        )


ObjectsService = ObjectsRequestSpecFactory
