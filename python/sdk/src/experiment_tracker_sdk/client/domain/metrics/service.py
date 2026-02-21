from typing import Any, Callable, cast

from uuid import UUID

from .dto import MetricCreateRequest, MetricResponse
from ...request import RequestSpec


class MetricService:
    ENDPOINTS = {
        "create_metric": "/api/metrics",
        "get_experiment_metrics": lambda experiment_id: f"/api/experiments/{experiment_id}/metrics",
        "get_project_metrics": lambda project_id: f"/api/projects/{project_id}/metrics",
    }

    def create_metric(
        self,
        experiment_id: str | UUID,
        name: str,
        value: float,
        step: int = 0,
        label: str | None = None,
    ) -> RequestSpec[MetricResponse]:
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
        return RequestSpec(
            method="POST",
            endpoint=endpoint,
            dto=payload,
            returning_dto=MetricResponse,
        )

    def get_experiment_metrics(self, experiment_id: str | UUID) -> RequestSpec[MetricResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint: str = cast(
            Callable[[Any], str], self.ENDPOINTS["get_experiment_metrics"]
        )(experiment_id)
        return RequestSpec(
            method="GET",
            endpoint=endpoint,
            returning_dto=MetricResponse,
            returning_dto_is_list=True,
        )

    def get_project_metrics(self, project_id: str | UUID) -> RequestSpec[MetricResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_project_metrics"])(
            project_id
        )
        return RequestSpec(
            method="GET",
            endpoint=endpoint,
            returning_dto=MetricResponse,
            returning_dto_is_list=True,
        )
