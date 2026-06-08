"""Proxy typed requests from the main backend to the internal MLTools API."""

from __future__ import annotations

from typing import TypeVar
from uuid import UUID

import httpx
from pydantic import BaseModel

from .dto import (
    MLToolsCreateJobDTO,
    MLToolsCreateJobResponseDTO,
    MLToolsJobDTO,
    MLToolsJobListDTO,
    MLToolsMessagesDTO,
    MLToolsResultsDTO,
)

DTO = TypeVar("DTO", bound=BaseModel)


class MLToolsClient:
    """Call trusted internal MLTools job, result, and message endpoints."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize the internal MLTools HTTP client.

        Args:
            base_url: Internal MLTools API base URL including its configured prefix.
            timeout: Per-request timeout in seconds.

        Result:
            MLToolsClient configured for trusted service-to-service requests.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _request(self, method: str, path: str, response_type: type[DTO], **kwargs) -> DTO:
        """Execute an internal request and validate its typed response.

        Args:
            method: HTTP method.
            path: Path relative to the configured MLTools base URL.
            response_type: Pydantic DTO type used to validate the response body.
            **kwargs: Additional keyword arguments forwarded to ``httpx``.

        Returns:
            DTO: Validated response model.

        Raises:
            httpx.HTTPStatusError: If MLTools returns a non-success status.
            httpx.RequestError: If MLTools is unavailable.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, f"{self.base_url}{path}", **kwargs)
            response.raise_for_status()
            return response_type.model_validate(response.json())

    async def create_job(self, project_id: UUID, payload: MLToolsCreateJobDTO) -> MLToolsCreateJobResponseDTO:
        """Create an asynchronous project importance job.

        Args:
            project_id: Project whose experiments should be analyzed.
            payload: Validated job creation request.

        Returns:
            MLToolsCreateJobResponseDTO: Persisted job identifier and initial status.
        """
        return await self._request(
            "POST",
            f"/projects/{project_id}/hparams/importance/jobs",
            MLToolsCreateJobResponseDTO,
            json=payload.model_dump(mode="json"),
        )

    async def list_jobs(self, project_id: UUID, limit: int, offset: int) -> MLToolsJobListDTO:
        """List project MLTools job history.

        Args:
            project_id: Project whose jobs are requested.
            limit: Maximum jobs to return.
            offset: Number of newest jobs to skip.

        Returns:
            MLToolsJobListDTO: Paginated job history.
        """
        return await self._request(
            "GET",
            f"/projects/{project_id}/hparams/importance/jobs",
            MLToolsJobListDTO,
            params={"limit": limit, "offset": offset},
        )

    async def get_job(self, project_id: UUID, job_id: UUID) -> MLToolsJobDTO:
        """Fetch one project-scoped job.

        Args:
            project_id: Project that must own the job.
            job_id: Job identifier.

        Returns:
            MLToolsJobDTO: Current lifecycle and progress metadata.
        """
        return await self._request(
            "GET", f"/projects/{project_id}/hparams/importance/jobs/{job_id}", MLToolsJobDTO
        )

    async def get_results(self, project_id: UUID, job_id: UUID) -> MLToolsResultsDTO:
        """Fetch grouped importance results for one job.

        Args:
            project_id: Project that must own the job.
            job_id: Job identifier.

        Returns:
            MLToolsResultsDTO: Ranked results grouped by target metric.
        """
        return await self._request(
            "GET",
            f"/projects/{project_id}/hparams/importance/jobs/{job_id}/results",
            MLToolsResultsDTO,
        )

    async def get_messages(self, project_id: UUID, job_id: UUID) -> MLToolsMessagesDTO:
        """Fetch persisted diagnostics for one job.

        Args:
            project_id: Project that must own the job.
            job_id: Job identifier.

        Returns:
            MLToolsMessagesDTO: Ordered informational, warning, and error messages.
        """
        return await self._request(
            "GET",
            f"/projects/{project_id}/hparams/importance/jobs/{job_id}/messages",
            MLToolsMessagesDTO,
        )
"""Typed HTTP client used by the main backend to orchestrate MLTools jobs."""
