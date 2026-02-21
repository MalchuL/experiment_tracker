from typing import Any, Callable, cast
from uuid import UUID

from .dto import (
    HypothesisCreateRequest,
    HypothesisResponse,
    HypothesisStatus,
    HypothesisUpdateRequest,
    SuccessResponse,
)
from ...constants import UNSET, Unset
from ...request import ApiRequestSpec


class HypothesisRequestSpecFactory:
    ENDPOINTS = {
        "create_hypothesis": "/api/hypotheses",
        "get_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "update_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "delete_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "get_project_hypotheses": lambda project_id: f"/api/projects/{project_id}/hypotheses",
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
        payload = HypothesisCreateRequest(
            projectId=project_id,
            title=title,
            description=description,
            author=author,
            status=status,
            targetMetrics=target_metrics or [],
            baseline=baseline,
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
            kwargs["title"] = title
        if description is not UNSET:
            kwargs["description"] = description
        if author is not UNSET:
            kwargs["author"] = author
        if status is not UNSET:
            kwargs["status"] = status
        if target_metrics is not UNSET:
            kwargs["targetMetrics"] = target_metrics
        if baseline is not UNSET:
            kwargs["baseline"] = baseline
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
        self, project_id: str | UUID
    ) -> ApiRequestSpec[HypothesisResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_project_hypotheses"])(
            project_id
        )
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=HypothesisResponse,
            response_is_list=True,
        )


# Backward-compatible alias.
HypothesisService = HypothesisRequestSpecFactory
