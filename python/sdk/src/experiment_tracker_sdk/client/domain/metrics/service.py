from typing import Any, Callable, cast
from uuid import UUID

from .dto import (
    MetricLabelsResponse,
    MetricListResponse,
    MetricResponse,
    MetricsByLabelSnapshotResponse,
    MetricUpsertRequest,
    UniqueMetricDimensionsResponse,
)
from ...request_types import ApiRequestSpec


class MetricRequestSpecFactory:
    ENDPOINTS = {
        "upsert_metric": "/metrics",
        "delete_metric": lambda metric_id: f"/metrics/{metric_id}",
        "get_experiment_metrics": lambda experiment_id: f"/experiments/{experiment_id}/metrics",
        "get_project_metrics": lambda project_id: f"/projects/{project_id}/metrics",
        "get_project_metric_labels": lambda project_id: f"/projects/{project_id}/metric-labels",
        "get_project_unique_metric_dimensions": lambda project_id: (
            f"/projects/{project_id}/metrics/unique-dimensions"
        ),
        "get_project_metrics_by_label": lambda project_id: (
            f"/projects/{project_id}/metrics/by-label"
        ),
    }

    def upsert_metric(
        self,
        experiment_id: str | UUID,
        name: str,
        value: float,
        label: str | None = None,
    ) -> ApiRequestSpec[MetricResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["upsert_metric"])
        payload = MetricUpsertRequest(
            experimentId=experiment_id,
            name=name,
            value=value,
            label=label,
        )
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=MetricResponse,
        )

    def delete_metric(self, metric_id: str | UUID) -> ApiRequestSpec[None]:
        if isinstance(metric_id, UUID):
            metric_id = str(metric_id)
        endpoint: str = cast(Callable[[Any], str], self.ENDPOINTS["delete_metric"])(
            metric_id
        )
        return ApiRequestSpec(method="DELETE", endpoint=endpoint, response_model=None)

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

    def get_project_metric_labels(
        self, project_id: str | UUID
    ) -> ApiRequestSpec[MetricLabelsResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint: str = cast(
            Callable[[Any], str], self.ENDPOINTS["get_project_metric_labels"]
        )(project_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=MetricLabelsResponse,
        )

    def get_project_unique_metric_dimensions(
        self, project_id: str | UUID
    ) -> ApiRequestSpec[UniqueMetricDimensionsResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint: str = cast(
            Callable[[Any], str], self.ENDPOINTS["get_project_unique_metric_dimensions"]
        )(project_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=UniqueMetricDimensionsResponse,
        )

    def get_project_metrics_by_label(
        self,
        project_id: str | UUID,
        label: str,
        *,
        include_experiments_without_metrics: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[MetricsByLabelSnapshotResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint: str = cast(
            Callable[[Any], str], self.ENDPOINTS["get_project_metrics_by_label"]
        )(project_id)
        q: dict[str, Any] = {
            "label": label,
            "include_experiments_without_metrics": include_experiments_without_metrics,
        }
        if limit is not None:
            q["limit"] = limit
        if offset is not None:
            q["offset"] = offset
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=MetricsByLabelSnapshotResponse,
            query_params=q,
        )


# Backward-compatible alias.
MetricService = MetricRequestSpecFactory
