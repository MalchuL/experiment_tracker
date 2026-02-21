from datetime import datetime
from typing import cast
from uuid import UUID

from .dto import (
    LastLoggedExperimentsRequest,
    LastLoggedExperimentsResponse,
    LogScalarRequest,
    LogScalarResponse,
    LogScalarsRequest,
    LogScalarsResponse,
    ScalarsPointsResponse,
)
from ...request import ApiRequestSpec


class ScalarsRequestSpecFactory:
    ENDPOINTS = {
        "log_scalar": lambda experiment_id: f"/api/scalars/log/{experiment_id}",
        "log_scalars_batch": lambda experiment_id: f"/api/scalars/log_batch/{experiment_id}",
        "get_scalars": lambda experiment_id: f"/api/scalars/get/{experiment_id}",
        "get_project_scalars": lambda project_id: f"/api/scalars/get/project/{project_id}",
        "get_last_logged_experiments": lambda project_id: f"/api/scalars/last_logged/{project_id}",
    }

    def log_scalar(
        self,
        experiment_id: str | UUID,
        scalars: dict[str, float],
        step: int,
        tags: list[str] | None = None,
    ) -> ApiRequestSpec[LogScalarResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["log_scalar"](experiment_id))
        payload = LogScalarRequest(scalars=scalars, step=step, tags=tags)
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=LogScalarResponse,
        )

    def log_scalars_batch(
        self, experiment_id: str | UUID, scalars: list[LogScalarRequest]
    ) -> ApiRequestSpec[LogScalarsResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["log_scalars_batch"](experiment_id))
        payload = LogScalarsRequest(scalars=scalars)
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=LogScalarsResponse,
        )

    def get_scalars(
        self,
        experiment_id: str | UUID,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ScalarsPointsResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["get_scalars"](experiment_id))
        params: dict[str, object] = {"return_tags": return_tags}
        if max_points is not None:
            params["max_points"] = max_points
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            query_params=params,
            response_model=ScalarsPointsResponse,
        )

    def get_project_scalars(
        self,
        project_id: str | UUID,
        experiment_ids: list[str] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ScalarsPointsResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["get_project_scalars"](project_id))
        params: dict[str, object] = {"return_tags": return_tags}
        if experiment_ids:
            params["experiment_id"] = experiment_ids
        if max_points is not None:
            params["max_points"] = max_points
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            query_params=params,
            response_model=ScalarsPointsResponse,
        )

    def get_last_logged_experiments(
        self, project_id: str | UUID, experiment_ids: list[str] | None = None
    ) -> ApiRequestSpec[LastLoggedExperimentsResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["get_last_logged_experiments"](project_id))
        payload = LastLoggedExperimentsRequest(experiment_ids=experiment_ids)
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=LastLoggedExperimentsResponse,
        )


# Backward-compatible alias.
ScalarsService = ScalarsRequestSpecFactory
