from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from experiment_tracker_shared.datetime_utc import to_json_utc_z

from .dto import (
    LastLoggedExperimentsRequest,
    LastLoggedExperimentsResponse,
    LogScalarRequest,
    LogScalarResponse,
    LogScalarsRequest,
    LogScalarsResponse,
    ScalarsPointsResponse,
)
from ...request_types import ApiRequestSpec

ScalarsSampling = Literal["uniform"]


class ScalarsRequestSpecFactory:
    ENDPOINTS = {
        "log_scalar": lambda experiment_id: f"/scalars/log/{experiment_id}",
        "log_scalars_batch": lambda experiment_id: f"/scalars/log_batch/{experiment_id}",
        "get_scalars": lambda experiment_id: f"/scalars/get/{experiment_id}",
        "get_project_scalars": lambda project_id: f"/scalars/get/project/{project_id}",
        "get_last_logged_experiments": lambda project_id: f"/scalars/last_logged/{project_id}",
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
        payload = LogScalarRequest(
            scalars=scalars,
            step=step,
            tags=tags,
        )
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
        normalized = [
            LogScalarRequest(
                scalars=row.scalars,
                step=row.step,
                tags=row.tags,
            )
            for row in scalars
        ]
        payload = LogScalarsRequest(scalars=normalized)
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=LogScalarsResponse,
        )

    def get_scalars(
        self,
        experiment_id: str | UUID,
        limit: int | None = None,
        offset: int | None = None,
        max_points: int | None = None,
        sampling: ScalarsSampling = "uniform",
        columns_per_query: int = 1,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ScalarsPointsResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["get_scalars"](experiment_id))
        params: dict[str, object] = {
            "return_tags": return_tags,
            "sampling": sampling,
            "columns_per_query": columns_per_query,
        }
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if max_points is not None:
            params["max_points"] = max_points
        if start_time is not None:
            params["start_time"] = to_json_utc_z(start_time)
        if end_time is not None:
            params["end_time"] = to_json_utc_z(end_time)
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
        limit: int | None = None,
        offset: int | None = None,
        max_points: int | None = None,
        sampling: ScalarsSampling = "uniform",
        columns_per_query: int = 1,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ScalarsPointsResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["get_project_scalars"](project_id))
        params: dict[str, object] = {
            "return_tags": return_tags,
            "sampling": sampling,
            "columns_per_query": columns_per_query,
        }
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if experiment_ids:
            params["experiment_id"] = experiment_ids
        if max_points is not None:
            params["max_points"] = max_points
        if start_time is not None:
            params["start_time"] = to_json_utc_z(start_time)
        if end_time is not None:
            params["end_time"] = to_json_utc_z(end_time)
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            query_params=params,
            response_model=ScalarsPointsResponse,
        )

    def get_last_logged_experiments(
        self,
        project_id: str | UUID,
        experiment_ids: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[LastLoggedExperimentsResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["get_last_logged_experiments"](project_id))
        payload = LastLoggedExperimentsRequest(experiment_ids=experiment_ids)
        query_params: dict[str, int] = {}
        if limit is not None:
            query_params["limit"] = limit
        if offset is not None:
            query_params["offset"] = offset
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=LastLoggedExperimentsResponse,
            query_params=query_params or None,
        )


# Backward-compatible alias.
ScalarsService = ScalarsRequestSpecFactory
