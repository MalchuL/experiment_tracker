"""Authorize and proxy MLTools hyperparameter-importance operations."""

from __future__ import annotations

from uuid import UUID

from clients.mltools import MLToolsClient
from clients.mltools.dto import (
    MLToolsCreateJobDTO,
    MLToolsCreateJobResponseDTO,
    MLToolsJobDTO,
    MLToolsJobListDTO,
    MLToolsMessagesDTO,
    MLToolsResultsDTO,
)
from domain.projects.errors import ProjectPermissionError
from domain.rbac.wrapper import PermissionChecker
from lib.protocols.user_protocol import UserProtocol


class MLToolsService:
    """Application service joining project permissions with the MLTools client."""

    def __init__(self, client: MLToolsClient, permission_checker: PermissionChecker):
        """Initialize the orchestration service.

        Args:
            client: HTTP adapter for the internal MLTools API.
            permission_checker: Main-backend project permission evaluator.
        """
        self.client = client
        self.permission_checker = permission_checker

    async def _require_read(self, user: UserProtocol, project_id: UUID) -> None:
        """Require both experiment and metric visibility for a project.

        Args:
            user: Authenticated user requesting MLTools data.
            project_id: Project against which permissions are evaluated.

        Returns:
            None after both permission checks pass.

        Raises:
            ProjectPermissionError: If either required read permission is absent.
        """
        if not await self.permission_checker.can_view_experiment(user.id, project_id):
            raise ProjectPermissionError("Experiment view permission is required")
        if not await self.permission_checker.can_view_metric(user.id, project_id):
            raise ProjectPermissionError("Metric view permission is required")

    async def create_job(
        self, user: UserProtocol, project_id: UUID, payload: MLToolsCreateJobDTO
    ) -> MLToolsCreateJobResponseDTO:
        """Authorize, attribute, and create an importance-analysis job.

        Args:
            user: Authenticated user creating the job.
            project_id: Project whose experiments will be analyzed.
            payload: Target metrics and requested analysis configuration.

        Returns:
            Identifier and initial state returned by MLTools.

        Raises:
            ProjectPermissionError: If edit or required read access is absent.
            httpx.HTTPError: If the internal MLTools request fails.
        """
        if not await self.permission_checker.can_edit_experiment(user.id, project_id):
            raise ProjectPermissionError("Experiment edit permission is required")
        await self._require_read(user, project_id)
        data = payload.model_copy(update={"requested_by_user_id": user.id})
        return await self.client.create_job(project_id, data)

    async def list_jobs(self, user: UserProtocol, project_id: UUID, limit: int, offset: int) -> MLToolsJobListDTO:
        """List project importance jobs after enforcing read permissions.

        Args:
            user: Authenticated user requesting job history.
            project_id: Project whose jobs are requested.
            limit: Maximum jobs to return.
            offset: Number of jobs to skip.

        Returns:
            Paginated importance-job history.

        Raises:
            ProjectPermissionError: If required read access is absent.
            httpx.HTTPError: If the internal MLTools request fails.
        """
        await self._require_read(user, project_id)
        return await self.client.list_jobs(project_id, limit, offset)

    async def get_job(self, user: UserProtocol, project_id: UUID, job_id: UUID) -> MLToolsJobDTO:
        """Fetch one project-owned importance job.

        Args:
            user: Authenticated user requesting the job.
            project_id: Project expected to own the job.
            job_id: Importance job identifier.

        Returns:
            Current job details.

        Raises:
            ProjectPermissionError: If required read access is absent.
            httpx.HTTPError: If the internal MLTools request fails.
        """
        await self._require_read(user, project_id)
        return await self.client.get_job(project_id, job_id)

    async def get_results(self, user: UserProtocol, project_id: UUID, job_id: UUID) -> MLToolsResultsDTO:
        """Fetch persisted importance results for one project-owned job.

        Args:
            user: Authenticated user requesting results.
            project_id: Project expected to own the job.
            job_id: Importance job identifier.

        Returns:
            Ranked per-metric importance results.

        Raises:
            ProjectPermissionError: If required read access is absent.
            httpx.HTTPError: If the internal MLTools request fails.
        """
        await self._require_read(user, project_id)
        return await self.client.get_results(project_id, job_id)

    async def get_messages(self, user: UserProtocol, project_id: UUID, job_id: UUID) -> MLToolsMessagesDTO:
        """Fetch persisted warnings and errors for one project-owned job.

        Args:
            user: Authenticated user requesting diagnostic messages.
            project_id: Project expected to own the job.
            job_id: Importance job identifier.

        Returns:
            Diagnostic messages emitted during analysis.

        Raises:
            ProjectPermissionError: If required read access is absent.
            httpx.HTTPError: If the internal MLTools request fails.
        """
        await self._require_read(user, project_id)
        return await self.client.get_messages(project_id, job_id)
