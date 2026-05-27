from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.domain.projects.dto import (
    ProjectMetricsResponse,
    ProjectOwnerResponse,
    ProjectResponse,
    ProjectSettingResponse,
    ProjectTeamResponse,
)
from experiment_tracker_sdk.client.api_access import resolve_client_and_registry

from .base import (
    ServerInstance,
    validate_uuid,
)


class ProjectBuilder:
    """Fluent builder for creating a project on the server.

    Args:
        request_client: Optional SDK HTTP client used to execute the create
            request. Defaults to the process-wide SDK client.
        api_requests_registry: Optional request-spec registry. Defaults to the
            process-wide SDK registry.

    The builder stores create-only inputs locally until ``create()`` is called.
    It does not issue any server requests before ``create()``.
    """

    def __init__(
        self,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> None:
        resolved = resolve_client_and_registry(
            request_client,
            api_requests_registry,
        )
        self._request_client = resolved.request_client
        self._api_requests_registry = resolved.api_requests_registry
        self._name: str | None = None
        self._description = ""
        self._metrics: ProjectMetricsResponse | None = None
        self._settings: list[ProjectSettingResponse] | None = None
        self._team_id: str | None = None

    def name(self, value: str) -> ProjectBuilder:
        self._name = value
        return self

    def description(self, value: str) -> ProjectBuilder:
        self._description = value
        return self

    def metrics(self, value: ProjectMetricsResponse) -> ProjectBuilder:
        self._metrics = value
        return self

    def settings(self, value: list[ProjectSettingResponse]) -> ProjectBuilder:
        self._settings = value
        return self

    def team_id(self, value: str | UUID | None) -> ProjectBuilder:
        self._team_id = validate_uuid(value, field_name="team_id")
        return self

    def create(self) -> ProjectInstance:
        if self._name is None:
            raise ValueError("Project name is required")
        response = cast(
            ProjectResponse,
            self._request_client.request(
                self._api_requests_registry.projects.create_project(
                    name=self._name,
                    description=self._description,
                    metrics=self._metrics,
                    settings=self._settings,
                    team_id=self._team_id,
                )
            ),
        )
        return ProjectInstance._from_response(
            response,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )


class ProjectInstance(ServerInstance):
    """SDK wrapper around one server-side project.

    Args:
        request_client: Optional SDK HTTP client used for fetch, update, and
            delete requests.
        api_requests_registry: Optional request-spec registry used to build
            project requests.

    Mutable properties:
        ``name``, ``description``, ``metrics`` and ``settings`` push project
        updates immediately unless the instance is inside a context manager.

    Read-only properties:
        ``id``, ``owner``, ``createdAt``, ``experimentCount``,
        ``hypothesisCount`` and ``team`` reflect server-computed fields.
    """

    _mutable_fields = frozenset({"name", "description", "metrics", "settings"})
    _id: str
    _name: str
    _description: str
    _metrics: ProjectMetricsResponse
    _settings: list[ProjectSettingResponse]
    _owner: ProjectOwnerResponse
    _createdAt: datetime
    _experimentCount: int
    _hypothesisCount: int
    _team: ProjectTeamResponse | None

    @classmethod
    def builder(
        cls,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> ProjectBuilder:
        return ProjectBuilder(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )

    @classmethod
    def fetch(
        cls,
        project_id: str | UUID,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> ProjectInstance:
        resolved = resolve_client_and_registry(
            request_client,
            api_requests_registry,
        )
        response = cast(
            ProjectResponse,
            resolved.request_client.request(
                resolved.api_requests_registry.projects.get_project(project_id)
            ),
        )
        return cls._from_response(
            response,
            request_client=resolved.request_client,
            api_requests_registry=resolved.api_requests_registry,
        )

    @classmethod
    def _from_response(
        cls,
        response: ProjectResponse,
        *,
        request_client: ExperimentTrackerClient,
        api_requests_registry: APIRequestsRegistry,
    ) -> ProjectInstance:
        """Build a hydrated project instance from a server response DTO.

        Args:
            response: Project response returned by create, fetch, or update.
            request_client: SDK HTTP client to bind to the instance.
            api_requests_registry: Request-spec registry to bind to the
                instance.

        Returns:
            Hydrated ``ProjectInstance`` with local fields copied from
            ``response``.
        """
        instance = cls(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )
        instance._hydrate(response)
        return instance

    @property
    def id(self) -> str:
        """Server-generated project id string. Read-only."""
        return str(self._id)

    @property
    def name(self) -> str:
        """Project display name. Assigning a value updates the server."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._set_mutable_field("name", value)

    @property
    def description(self) -> str:
        """Project description. Assigning a value updates the server."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._set_mutable_field("description", value)

    @property
    def metrics(self) -> ProjectMetricsResponse:
        """Project metric configuration. Assigning a value updates the server."""
        return self._metrics

    @metrics.setter
    def metrics(self, value: ProjectMetricsResponse) -> None:
        self._set_mutable_field("metrics", value)

    @property
    def settings(self) -> list[ProjectSettingResponse]:
        """Project settings configuration. Assigning a value updates the server."""
        return self._settings

    @settings.setter
    def settings(self, value: list[ProjectSettingResponse]) -> None:
        self._set_mutable_field("settings", value)

    @property
    def owner(self) -> ProjectOwnerResponse:
        """Project owner metadata returned by the server. Read-only."""
        return self._owner

    @property
    def createdAt(self) -> datetime:
        """Project creation timestamp returned by the server. Read-only."""
        return self._createdAt

    @property
    def experimentCount(self) -> int:
        """Number of experiments in the project returned by the server. Read-only."""
        return self._experimentCount

    @property
    def hypothesisCount(self) -> int:
        """Number of hypotheses in the project returned by the server. Read-only."""
        return self._hypothesisCount

    @property
    def team(self) -> ProjectTeamResponse | None:
        """Team metadata for team-owned projects, or ``None``. Read-only."""
        return self._team

    def _push_update(self, changes: dict) -> None:
        """Send one project update request for pending mutable field changes.

        Args:
            changes: Partial project update containing any of ``name``,
                ``description``, ``metrics`` or ``settings``.
        """
        response = cast(
            ProjectResponse,
            self._request(
                self.api_requests_registry.projects.update_project(
                    self.id,
                    name=changes.get("name"),
                    description=changes.get("description"),
                    metrics=changes.get("metrics"),
                    settings=changes.get("settings"),
                )
            ),
        )
        self._hydrate(response)

    def delete(self) -> None:
        """Delete the project on the server and block later local updates."""
        self._ensure_not_deleted()
        self._request(self.api_requests_registry.projects.delete_project(self.id))
        self._deleted = True
