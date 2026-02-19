from typing import Any, Callable, cast
from uuid import UUID

from .dto import (
    HypothesisCreateRequest,
    HypothesisResponse,
    HypothesisStatus,
    HypothesisUpdateRequest,
    SuccessResponse,
)
from ...client import ExperimentTrackerClient
from ...constants import UNSET, Unset


class HypothesisService:
    ENDPOINTS = {
        "create_hypothesis": "/api/hypotheses",
        "get_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "update_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "delete_hypothesis": lambda hypothesis_id: f"/api/hypotheses/{hypothesis_id}",
        "get_project_hypotheses": lambda project_id: f"/api/projects/{project_id}/hypotheses",
    }

    def __init__(self, client: ExperimentTrackerClient):
        self._client = client

    def get_hypothesis(self, hypothesis_id: str | UUID) -> HypothesisResponse:
        if isinstance(hypothesis_id, UUID):
            hypothesis_id = str(hypothesis_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_hypothesis"])(
            hypothesis_id
        )
        response = self._client.request("GET", endpoint)
        return HypothesisResponse.model_validate(response.json())

    def create_hypothesis(
        self,
        project_id: str | UUID,
        title: str,
        author: str,
        description: str = "",
        status: HypothesisStatus = HypothesisStatus.PROPOSED,
        target_metrics: list[str] | None = None,
        baseline: str = "root",
    ) -> HypothesisResponse:
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
        response = self._client.request("POST", endpoint, json=payload)
        return HypothesisResponse.model_validate(response.json())

    def update_hypothesis(
        self,
        hypothesis_id: str | UUID,
        title: str | Unset = UNSET,
        description: str | Unset = UNSET,
        author: str | Unset = UNSET,
        status: HypothesisStatus | Unset = UNSET,
        target_metrics: list[str] | Unset = UNSET,
        baseline: str | Unset = UNSET,
    ) -> HypothesisResponse:
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
        response = self._client.request("PATCH", endpoint, json=payload)
        return HypothesisResponse.model_validate(response.json())

    def delete_hypothesis(self, hypothesis_id: str | UUID) -> SuccessResponse:
        if isinstance(hypothesis_id, UUID):
            hypothesis_id = str(hypothesis_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["delete_hypothesis"])(
            hypothesis_id
        )
        response = self._client.request("DELETE", endpoint)
        return SuccessResponse.model_validate(response.json())

    def get_project_hypotheses(
        self, project_id: str | UUID
    ) -> list[HypothesisResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(Callable[[Any], str], self.ENDPOINTS["get_project_hypotheses"])(
            project_id
        )
        response = self._client.request("GET", endpoint)
        return [HypothesisResponse.model_validate(item) for item in response.json()]
