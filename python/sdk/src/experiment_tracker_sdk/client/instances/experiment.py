from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.constants import UNSET
from experiment_tracker_sdk.client.domain.experiments.dto import (
    ExperimentResponse,
    ExperimentStatus,
    FeatureNodeLike,
)

from .base import (
    ServerInstance,
    resolve_client_and_registry,
    validate_hex_color,
    validate_uuid,
)


class ExperimentBuilder:
    """Fluent builder for creating an experiment on the server.

    Args:
        request_client: Optional SDK HTTP client used to execute the create
            request. Defaults to the process-wide SDK client.
        api_requests_registry: Optional request-spec registry. Defaults to the
            process-wide SDK registry.

    The builder stores required ``project_id`` and ``name`` plus optional
    experiment fields until ``create()`` is called.
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
        self._project_id: str | None = None
        self._name: str | None = None
        self._description = ""
        self._color = UNSET
        self._parent_experiment_id = UNSET
        self._features = UNSET
        self._status = ExperimentStatus.PLANNED
        self._tags = UNSET

    def project_id(self, value: str | UUID) -> ExperimentBuilder:
        self._project_id = validate_uuid(
            value,
            field_name="project_id",
            required=True,
        )
        return self

    def name(self, value: str) -> ExperimentBuilder:
        self._name = value
        return self

    def description(self, value: str) -> ExperimentBuilder:
        self._description = value
        return self

    def color(self, value: str | None) -> ExperimentBuilder:
        self._color = validate_hex_color(value)
        return self

    def parent_experiment_id(self, value: str | UUID | None) -> ExperimentBuilder:
        self._parent_experiment_id = validate_uuid(
            value,
            field_name="parent_experiment_id",
        )
        return self

    def features(self, value: list[FeatureNodeLike]) -> ExperimentBuilder:
        self._features = value
        return self

    def status(self, value: ExperimentStatus) -> ExperimentBuilder:
        self._status = value
        return self

    def tags(self, value: list[str] | None) -> ExperimentBuilder:
        self._tags = value
        return self

    def create(self) -> ExperimentInstance:
        if self._project_id is None:
            raise ValueError("Experiment project_id is required")
        if self._name is None:
            raise ValueError("Experiment name is required")
        response = cast(
            ExperimentResponse,
            self._request_client.request(
                self._api_requests_registry.experiments.create_experiment(
                    project_id=self._project_id,
                    name=self._name,
                    description=self._description,
                    color=self._color,
                    parent_experiment_id=self._parent_experiment_id,
                    features=self._features,
                    status=self._status,
                    tags=self._tags,
                )
            ),
        )
        return ExperimentInstance._from_response(
            response,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )


class ExperimentInstance(ServerInstance):
    """SDK wrapper around one server-side experiment.

    Args:
        request_client: Optional SDK HTTP client used for fetch, update, and
            delete requests.
        api_requests_registry: Optional request-spec registry used to build
            experiment requests.

    Mutable properties:
        ``name``, ``description``, ``color``, ``parentExperimentId``,
        ``features``, ``status``, ``progress`` and ``tags`` push experiment
        updates immediately unless the instance is inside a context manager.

    Read-only properties:
        ``id``, ``projectId``, ``createdAt``, ``startedAt`` and ``completedAt``
        reflect server-computed fields.
    """

    _mutable_fields = frozenset(
        {
            "name",
            "description",
            "color",
            "parentExperimentId",
            "features",
            "status",
            "progress",
            "tags",
        }
    )
    _id: str
    _projectId: str
    _name: str
    _description: str
    _status: str
    _color: str | None
    _tags: list[str] | None
    _parentExperimentId: str | None
    _features: list[FeatureNodeLike]
    _progress: int | None
    _createdAt: datetime
    _startedAt: datetime | None
    _completedAt: datetime | None

    @classmethod
    def builder(
        cls,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> ExperimentBuilder:
        return ExperimentBuilder(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )

    @classmethod
    def fetch(
        cls,
        experiment_id: str | UUID,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> ExperimentInstance:
        request_client, api_requests_registry = resolve_client_and_registry(
            request_client,
            api_requests_registry,
        )
        response = cast(
            ExperimentResponse,
            request_client.request(
                api_requests_registry.experiments.get_experiment(experiment_id)
            ),
        )
        return cls._from_response(
            response,
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )

    @classmethod
    def _from_response(
        cls,
        response: ExperimentResponse,
        *,
        request_client: ExperimentTrackerClient,
        api_requests_registry: APIRequestsRegistry,
    ) -> ExperimentInstance:
        """Build a hydrated experiment instance from a server response DTO.

        Args:
            response: Experiment response returned by create, fetch, or update.
            request_client: SDK HTTP client to bind to the instance.
            api_requests_registry: Request-spec registry to bind to the
                instance.

        Returns:
            Hydrated ``ExperimentInstance`` with local fields copied from
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
        """Server-generated experiment id string. Read-only."""
        return str(self._id)

    @property
    def projectId(self) -> str:
        """Project id that owns this experiment. Read-only."""
        return str(self._projectId)

    @property
    def name(self) -> str:
        """Experiment display name. Assigning a value updates the server."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._set_mutable_field("name", value)

    @property
    def description(self) -> str:
        """Experiment description. Assigning a value updates the server."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._set_mutable_field("description", value)

    @property
    def status(self) -> str:
        """Experiment status. Assigning an ``ExperimentStatus`` updates the server."""
        return self._status

    @status.setter
    def status(self, value: ExperimentStatus) -> None:
        self._set_mutable_field("status", value)

    @property
    def color(self) -> str | None:
        """Experiment color string, usually a hex color. Assigning updates the server."""
        return self._color

    @color.setter
    def color(self, value: str | None) -> None:
        self._set_mutable_field("color", validate_hex_color(value))

    @property
    def tags(self) -> list[str] | None:
        """Experiment tags. Assigning a list or ``None`` updates the server."""
        return self._tags

    @tags.setter
    def tags(self, value: list[str] | None) -> None:
        self._set_mutable_field("tags", value)

    @property
    def parentExperimentId(self) -> str | None:
        """Parent experiment id, if any. Assigning updates the server."""
        return (
            None
            if self._parentExperimentId is None
            else str(self._parentExperimentId)
        )

    @parentExperimentId.setter
    def parentExperimentId(self, value: str | UUID | None) -> None:
        self._set_mutable_field(
            "parentExperimentId",
            validate_uuid(value, field_name="parentExperimentId"),
        )

    @property
    def features(self) -> list[FeatureNodeLike]:
        """Experiment feature tree. Assigning a list updates the server."""
        return self._features

    @features.setter
    def features(self, value: list[FeatureNodeLike]) -> None:
        self._set_mutable_field("features", value)

    @property
    def progress(self) -> int | None:
        """Experiment progress percentage. Assigning a value updates the server."""
        return self._progress

    @progress.setter
    def progress(self, value: int | None) -> None:
        self._set_mutable_field("progress", value)

    @property
    def createdAt(self) -> datetime:
        """Experiment creation timestamp returned by the server. Read-only."""
        return self._createdAt

    @property
    def startedAt(self) -> datetime | None:
        """Experiment start timestamp returned by the server. Read-only."""
        return self._startedAt

    @property
    def completedAt(self) -> datetime | None:
        """Experiment completion timestamp returned by the server. Read-only."""
        return self._completedAt

    def _push_update(self, changes: dict) -> None:
        """Send one experiment update request for pending mutable field changes.

        Args:
            changes: Partial experiment update containing any mutable experiment
                field. Missing fields are passed as ``UNSET`` so they are
                omitted from the PATCH payload.
        """
        response = cast(
            ExperimentResponse,
            self._request(
                self.api_requests_registry.experiments.update_experiment(
                    self.id,
                    name=changes.get("name", UNSET),
                    description=changes.get("description", UNSET),
                    color=changes.get("color", UNSET),
                    parent_experiment_id=changes.get("parentExperimentId", UNSET),
                    features=changes.get("features", UNSET),
                    status=changes.get("status", UNSET),
                    progress=changes.get("progress", UNSET),
                    tags=changes.get("tags", UNSET),
                )
            ),
        )
        self._hydrate(response)

    def delete(self) -> None:
        """Delete the experiment on the server and block later local updates."""
        self._ensure_not_deleted()
        self._request(self.api_requests_registry.experiments.delete_experiment(self.id))
        self._deleted = True
