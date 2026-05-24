from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.domain.teams.dto import TeamResponse

from .base import ServerInstance, resolve_client_and_registry


class TeamBuilder:
    """Fluent builder for creating a team on the server.

    Args:
        request_client: Optional SDK HTTP client used to execute the create
            request. Defaults to the process-wide SDK client.
        api_requests_registry: Optional request-spec registry. Defaults to the
            process-wide SDK registry.

    The builder collects ``name`` and optional ``description`` until
    ``create()`` is called.
    """

    def __init__(
        self,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> None:
        self._request_client, self._api_requests_registry = resolve_client_and_registry(
            request_client,
            api_requests_registry,
        )
        self._name: str | None = None
        self._description: str | None = None

    def name(self, value: str) -> TeamBuilder:
        self._name = value
        return self

    def description(self, value: str | None) -> TeamBuilder:
        self._description = value
        return self

    def create(self) -> TeamInstance:
        if self._name is None:
            raise ValueError("Team name is required")
        response = cast(
            TeamResponse,
            self._request_client.request(
                self._api_requests_registry.teams.create_team(
                    self._name,
                    description=self._description,
                )
            ),
        )
        return TeamInstance._from_response(
            response,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )


class TeamInstance(ServerInstance):
    """SDK wrapper around one server-side team.

    Args:
        request_client: Optional SDK HTTP client used for fetch, update, and
            delete requests.
        api_requests_registry: Optional request-spec registry used to build team
            requests.

    Mutable properties:
        ``name`` and ``description`` push team updates immediately unless the
        instance is inside a context manager.

    Read-only properties:
        ``id``, ``createdAt`` and ``ownerId`` reflect server-computed fields.
    """

    _mutable_fields = frozenset({"name", "description"})
    _id: str
    _createdAt: datetime
    _ownerId: str | None
    _name: str
    _description: str | None

    @classmethod
    def builder(
        cls,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> TeamBuilder:
        return TeamBuilder(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )

    @classmethod
    def fetch(
        cls,
        team_id: str | UUID,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> TeamInstance:
        request_client, api_requests_registry = resolve_client_and_registry(
            request_client,
            api_requests_registry,
        )
        response = cast(
            TeamResponse,
            request_client.request(api_requests_registry.teams.get_team(team_id)),
        )
        return cls._from_response(
            response,
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )

    @classmethod
    def _from_response(
        cls,
        response: TeamResponse,
        *,
        request_client: ExperimentTrackerClient,
        api_requests_registry: APIRequestsRegistry,
    ) -> TeamInstance:
        """Build a hydrated team instance from a server response DTO.

        Args:
            response: Team response returned by create, fetch, or update.
            request_client: SDK HTTP client to bind to the instance.
            api_requests_registry: Request-spec registry to bind to the
                instance.

        Returns:
            Hydrated ``TeamInstance`` with local fields copied from ``response``.
        """
        instance = cls(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )
        instance._hydrate(response)
        return instance

    @property
    def id(self) -> str:
        """Server-generated team id string. Read-only."""
        return str(self._id)

    @property
    def createdAt(self) -> datetime:
        """Team creation timestamp returned by the server. Read-only."""
        return self._createdAt

    @property
    def ownerId(self) -> str | None:
        """User id of the team owner when returned. Read-only."""
        return None if self._ownerId is None else str(self._ownerId)

    @property
    def name(self) -> str:
        """Team display name. Assigning a value updates the server."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._set_mutable_field("name", value)

    @property
    def description(self) -> str | None:
        """Team description. Assigning a value updates the server."""
        return self._description

    @description.setter
    def description(self, value: str | None) -> None:
        self._set_mutable_field("description", value)

    def _push_update(self, changes: dict) -> None:
        """Send one team update request for pending mutable field changes.

        Args:
            changes: Partial team update containing ``name`` and/or
                ``description``. The backend requires ``name``, so the current
                local value is used when only ``description`` changed.
        """
        response = cast(
            TeamResponse,
            self._request(
                self.api_requests_registry.teams.update_team(
                    self.id,
                    name=changes.get("name", self.name),
                    description=changes.get("description", self.description),
                )
            ),
        )
        self._hydrate(response)

    def delete(self) -> None:
        """Delete the team on the server and block later local updates."""
        self._ensure_not_deleted()
        self._request(self.api_requests_registry.teams.delete_team(self.id))
        self._deleted = True
