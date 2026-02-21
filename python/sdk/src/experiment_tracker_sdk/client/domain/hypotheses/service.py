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
from ...request import RequestSpec


class HypothesisService:
    ENDPOINTS = {
        "create_hypothesis": "/api/hypotheses",
        "get_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "update_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "delete_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "get_project_hypotheses": lambda project_id: f"/api/projects/{project_id}/hypotheses",
    }

    def get_hypothesis(self, hypothesis_id: str | UUID) -> RequestSpec[HypothesisResponse]:
        if isinstance(hypothesis_id, UUID):
            hypothesis_id = str(hypothesis_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_hypothesis"])(
            hypothesis_id
        )
        return RequestSpec(
            method="GET",
            endpoint=endpoint,
            returning_dto=HypothesisResponse,
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
    ) -> RequestSpec[HypothesisResponse]:
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
        return RequestSpec(
            method="POST",
            endpoint=endpoint,
            dto=payload,
            returning_dto=HypothesisResponse,
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
    ) -> RequestSpec[HypothesisResponse]:
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
        return RequestSpec(
            method="PATCH",
            endpoint=endpoint,
            dto=payload,
            returning_dto=HypothesisResponse,
        )

    def delete_hypothesis(self, hypothesis_id: str | UUID) -> RequestSpec[SuccessResponse]:
        if isinstance(hypothesis_id, UUID):
            hypothesis_id = str(hypothesis_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["delete_hypothesis"])(
            hypothesis_id
        )
        return RequestSpec(
            method="DELETE",
            endpoint=endpoint,
            returning_dto=SuccessResponse,
        )

    def get_project_hypotheses(
        self, project_id: str | UUID
    ) -> RequestSpec[HypothesisResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_project_hypotheses"])(
            project_id
        )
        return RequestSpec(
            method="GET",
            endpoint=endpoint,
            returning_dto=HypothesisResponse,
            returning_dto_is_list=True,
        )
