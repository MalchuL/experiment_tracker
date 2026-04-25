from typing import Any, Callable, cast

from uuid import UUID

from .dto import MetricCreateRequest, MetricListResponse, MetricResponse
from ...request_types import ApiRequestSpec


class MetricRequestSpecFactory:
    ENDPOINTS = {
        "create_metric": "/metrics",
        "get_experiment_metrics": lambda experiment_id: f"/experiments/{experiment_id}/metrics",
        "get_project_metrics": lambda project_id: f"/projects/{project_id}/metrics",
    }

    def create_metric(
        self,
        experiment_id: str | UUID,
        name: str,
        value: float,
        step: int = 0,
        label: str | None = None,
    ) -> ApiRequestSpec[MetricResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["create_metric"])
        payload = MetricCreateRequest(
            experimentId=experiment_id,
            name=name,
            value=value,
            step=step,
            label=label,
        )
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=MetricResponse,
        )

    def get_experiment_metrics(
        self,
        experiment_id: str | UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[MetricListResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint: str = cast(
            Callable[[Any], str], self.ENDPOINTS["get_experiment_metrics"]
        )(experiment_id)
        query_params: dict[str, int] = {}
        if limit is not None:
            query_params["limit"] = limit
        if offset is not None:
            query_params["offset"] = offset
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=MetricListResponse,
            query_params=query_params or None,
        )

    def get_project_metrics(
        self,
        project_id: str | UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[MetricListResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_project_metrics"])(
            project_id
        )
        query_params: dict[str, int] = {}
        if limit is not None:
            query_params["limit"] = limit
        if offset is not None:
            query_params["offset"] = offset
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=MetricListResponse,
            query_params=query_params or None,
        )


# Backward-compatible alias.
MetricService = MetricRequestSpecFactory
