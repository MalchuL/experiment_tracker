"""Authorization and attribution tests for backend MLTools orchestration."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from clients.mltools.dto import MLToolsCreateJobDTO, MLToolsTargetMetricDTO
from domain.mltools.service import MLToolsService
from domain.projects.errors import ProjectPermissionError


class Permissions:
    """Configurable permission-checker fake used by orchestration tests."""

    def __init__(self, *, edit=True, view_experiment=True, view_metric=True):
        """Initialize permission outcomes.

        Args:
            edit: Whether experiment edit checks succeed.
            view_experiment: Whether experiment view checks succeed.
            view_metric: Whether metric view checks succeed.

        Returns:
            None.
        """
        self.edit = edit
        self.view_experiment = view_experiment
        self.view_metric = view_metric

    async def can_edit_experiment(self, user_id, project_id):
        """Return the configured experiment-edit decision.

        Args:
            user_id: Ignored user identifier required by the checker contract.
            project_id: Ignored project identifier required by the contract.

        Returns:
            Configured edit permission.
        """
        return self.edit

    async def can_view_experiment(self, user_id, project_id):
        """Return the configured experiment-view decision.

        Args:
            user_id: Ignored user identifier required by the checker contract.
            project_id: Ignored project identifier required by the contract.

        Returns:
            Configured experiment-view permission.
        """
        return self.view_experiment

    async def can_view_metric(self, user_id, project_id):
        """Return the configured metric-view decision.

        Args:
            user_id: Ignored user identifier required by the checker contract.
            project_id: Ignored project identifier required by the contract.

        Returns:
            Configured metric-view permission.
        """
        return self.view_metric


class Client:
    """Capture job-creation payloads sent by the orchestration service."""

    def __init__(self):
        """Initialize the client without a captured payload.

        Args:
            None.

        Returns:
            None.
        """
        self.payload = None

    async def create_job(self, project_id, payload):
        """Capture a creation payload and return a pending job response.

        Args:
            project_id: Ignored project identifier required by the client port.
            payload: Job creation DTO to capture for assertions.

        Returns:
            Minimal pending-job response object.
        """
        self.payload = payload
        return SimpleNamespace(job_id=uuid4(), status="pending")


@pytest.mark.asyncio
async def test_create_job_records_authenticated_user() -> None:
    client = Client()
    service = MLToolsService(client, Permissions())  # type: ignore[arg-type]
    user = SimpleNamespace(id=uuid4())

    await service.create_job(
        user,
        uuid4(),
        MLToolsCreateJobDTO(target_metrics=[MLToolsTargetMetricDTO(name="loss")]),
    )

    assert client.payload.requested_by_user_id == user.id


@pytest.mark.asyncio
async def test_create_requires_edit_and_reads_require_both_view_permissions() -> None:
    user = SimpleNamespace(id=uuid4())
    project_id = uuid4()
    payload = MLToolsCreateJobDTO(target_metrics=[MLToolsTargetMetricDTO(name="loss")])

    with pytest.raises(ProjectPermissionError):
        await MLToolsService(Client(), Permissions(edit=False)).create_job(user, project_id, payload)  # type: ignore[arg-type]
    with pytest.raises(ProjectPermissionError):
        await MLToolsService(Client(), Permissions(view_metric=False)).list_jobs(user, project_id, 20, 0)  # type: ignore[arg-type]
