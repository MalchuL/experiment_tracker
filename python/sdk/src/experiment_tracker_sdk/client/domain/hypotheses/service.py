from typing import Any, Callable, cast
from uuid import UUID

from .dto import (
    HypothesisCreateRequest,
    HypothesisListResponse,
    HypothesisResponse,
    HypothesisStatus,
    HypothesisUpdateRequest,
    SuccessResponse,
)
from .limits import (
    truncate_hypothesis_author,
    truncate_hypothesis_baseline,
    truncate_hypothesis_description,
    truncate_hypothesis_target_metric_name,
    truncate_hypothesis_title,
)
from ...constants import UNSET, Unset
from ...request_types import ApiRequestSpec


class HypothesisRequestSpecFactory:
    ENDPOINTS = {
        "create_hypothesis": "/hypotheses",
        "get_recent_hypotheses": "/hypotheses/recent",
        "get_hypothesis": lambda hypothesis_id: f"/hypotheses/{hypothesis_id}",
        "update_hypothesis": lambda hypothesis_id: f"/hypotheses/{hypothesis_id}",
        "delete_hypothesis": lambda hypothesis_id: f"/hypotheses/{hypothesis_id}",
        "get_project_hypotheses": lambda project_id: f"/projects/{project_id}/hypotheses",
    }

    def get_hypothesis(self, hypothesis_id: str | UUID) -> ApiRequestSpec[HypothesisResponse]:
        if isinstance(hypothesis_id, UUID):
            hypothesis_id = str(hypothesis_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_hypothesis"])(
            hypothesis_id
        )
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=HypothesisResponse,
        )

    def create_hypothesis(
        self,
        project_id: str | UUID,
        title: str,
        author: str,
        description: str = "",
        status: HypothesisStatus = HypothesisStatus.PROPOSED,
        target_metrics: list[str] | None = None,
        baseline: str = "root",
    ) -> ApiRequestSpec[HypothesisResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["create_hypothesis"])
        t_metrics = [truncate_hypothesis_target_metric_name(m) for m in (target_metrics or [])]
        payload = HypothesisCreateRequest(
            projectId=project_id,
            title=truncate_hypothesis_title(title),
            description=truncate_hypothesis_description(description),
            author=truncate_hypothesis_author(author),
            status=status,
            targetMetrics=t_metrics,
            baseline=truncate_hypothesis_baseline(baseline),
        )
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=HypothesisResponse,
        )

    def update_hypothesis(
        self,
        hypothesis_id: str | UUID,
        title: str | Unset = UNSET,
        description: str | Unset = UNSET,
        author: str | Unset = UNSET,
        status: HypothesisStatus | Unset = UNSET,
        target_metrics: list[str] | Unset = UNSET,
        baseline: str | Unset = UNSET,
    ) -> ApiRequestSpec[HypothesisResponse]:
        if isinstance(hypothesis_id, UUID):
            hypothesis_id = str(hypothesis_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["update_hypothesis"])(
            hypothesis_id
        )
        kwargs: dict[str, Any] = {}
        if title is not UNSET:
            kwargs["title"] = truncate_hypothesis_title(title)
        if description is not UNSET:
            kwargs["description"] = truncate_hypothesis_description(description)
        if author is not UNSET:
            kwargs["author"] = truncate_hypothesis_author(author)
        if status is not UNSET:
            kwargs["status"] = status
        if target_metrics is not UNSET:
            kwargs["targetMetrics"] = [
                truncate_hypothesis_target_metric_name(m) for m in target_metrics
            ]
        if baseline is not UNSET:
            kwargs["baseline"] = truncate_hypothesis_baseline(baseline)
        payload = HypothesisUpdateRequest(**kwargs)
        return ApiRequestSpec(
            method="PATCH",
            endpoint=endpoint,
            request_payload=payload,
            response_model=HypothesisResponse,
        )

    def delete_hypothesis(self, hypothesis_id: str | UUID) -> ApiRequestSpec[SuccessResponse]:
        if isinstance(hypothesis_id, UUID):
            hypothesis_id = str(hypothesis_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["delete_hypothesis"])(
            hypothesis_id
        )
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=SuccessResponse,
        )

    def get_project_hypotheses(
        self,
        project_id: str | UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[HypothesisListResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_project_hypotheses"])(
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
            response_model=HypothesisListResponse,
            query_params=query_params or None,
        )

    def get_recent_hypotheses(
        self,
        project_id: str | UUID,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[HypothesisListResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["get_recent_hypotheses"])
        query_params: dict[str, str | int] = {"projectId": project_id}
        if limit is not None:
            query_params["limit"] = limit
        if offset is not None:
            query_params["offset"] = offset
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=HypothesisListResponse,
            query_params=query_params,
        )


# Backward-compatible alias.
HypothesisService = HypothesisRequestSpecFactory
