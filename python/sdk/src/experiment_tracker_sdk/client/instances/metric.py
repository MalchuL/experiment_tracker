from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.api_access import resolve_client_and_registry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.domain.metrics.dto import MetricResponse

from .base import (
    ServerInstance,
    validate_uuid,
)


class MetricBuilder:
    """Fluent builder for creating or upserting a metric row on the server.

    Args:
        request_client: Optional SDK HTTP client used to execute the upsert
            request. Defaults to the process-wide SDK client.
        api_requests_registry: Optional request-spec registry. Defaults to the
            process-wide SDK registry.

    Metrics are unique by ``(experiment_id, name, label)``. Calling ``create()``
    sends the same upsert request used by the rest of the SDK.
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
        self._experiment_id: str | None = None
        self._name: str | None = None
        self._value: float | None = None
        self._label: str | None = None

    def experiment_id(self, value: str | UUID) -> MetricBuilder:
        self._experiment_id = validate_uuid(
            value,
            field_name="experiment_id",
            required=True,
        )
        return self

    def name(self, value: str) -> MetricBuilder:
        self._name = value
        return self

    def value(self, value: float) -> MetricBuilder:
        self._value = value
        return self

    def label(self, value: str | None) -> MetricBuilder:
        self._label = value
        return self

    def create(self) -> MetricInstance:
        if self._experiment_id is None:
            raise ValueError("Metric experiment_id is required")
        if self._name is None:
            raise ValueError("Metric name is required")
        if self._value is None:
            raise ValueError("Metric value is required")
        response = cast(
            MetricResponse,
            self._request_client.request(
                self._api_requests_registry.metrics.upsert_metric(
                    experiment_id=self._experiment_id,
                    name=self._name,
                    value=self._value,
                    label=self._label,
                )
            ),
        )
        return MetricInstance._from_response(
            response,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )


class MetricInstance(ServerInstance):
    """SDK wrapper around one server-side metric.

    Args:
        request_client: Optional SDK HTTP client used for fetch, upsert, and
            delete requests.
        api_requests_registry: Optional request-spec registry used to build
            metric requests.

    Mutable properties:
        ``experimentId``, ``name``, ``value`` and ``label`` push metric upserts
        immediately unless the instance is inside a context manager.

    Read-only properties:
        ``id`` and ``createdAt`` reflect server-computed fields. Updating key
        fields uses metric upsert semantics and refreshes the local instance
        from the server response.
    """

    _mutable_fields = frozenset({"experimentId", "name", "value", "label"})
    _id: str
    _experimentId: str
    _name: str
    _value: float
    _label: str | None
    _createdAt: datetime

    @classmethod
    def builder(
        cls,
        *,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> MetricBuilder:
        return MetricBuilder(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )

    @classmethod
    def fetch(
        cls,
        *,
        experiment_id: str | UUID,
        name: str,
        label: str | None = None,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> MetricInstance:
        resolved = resolve_client_and_registry(
            request_client,
            api_requests_registry,
        )
        response = cast(
            MetricResponse,
            resolved.request_client.request(
                resolved.api_requests_registry.metrics.get_metric(
                    experiment_id=experiment_id,
                    name=name,
                    label=label,
                )
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
        response: MetricResponse,
        *,
        request_client: ExperimentTrackerClient,
        api_requests_registry: APIRequestsRegistry,
    ) -> MetricInstance:
        """Build a hydrated metric instance from a server response DTO.

        Args:
            response: Metric response returned by create, fetch, or upsert.
            request_client: SDK HTTP client to bind to the instance.
            api_requests_registry: Request-spec registry to bind to the
                instance.

        Returns:
            Hydrated ``MetricInstance`` with local fields copied from
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
        """Server-generated metric id string. Read-only."""
        return str(self._id)

    @property
    def experimentId(self) -> str:
        """Experiment id for this metric. Assigning upserts."""
        return str(self._experimentId)

    @experimentId.setter
    def experimentId(self, value: str | UUID) -> None:
        self._set_mutable_field(
            "experimentId",
            validate_uuid(value, field_name="experimentId", required=True),
        )

    @property
    def name(self) -> str:
        """Metric name. Assigning a value upserts the metric."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._set_mutable_field("name", value)

    @property
    def value(self) -> float:
        """Metric value. Assigning a value upserts the metric."""
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        self._set_mutable_field("value", value)

    @property
    def label(self) -> str | None:
        """Metric label, or ``None`` for unlabeled metrics. Assigning upserts."""
        return self._label

    @label.setter
    def label(self, value: str | None) -> None:
        self._set_mutable_field("label", value)

    @property
    def createdAt(self) -> datetime:
        """Metric creation timestamp returned by the server. Read-only."""
        return self._createdAt

    def _push_update(self, changes: dict) -> None:
        """Send one metric upsert request for pending mutable field changes.

        Args:
            changes: Partial metric change set. Missing key fields use the
                current local ``experimentId``, ``name`` and ``label`` values;
                missing ``value`` uses the current local value.
        """
        experiment_id = changes.get("experimentId", self.experimentId)
        name = changes.get("name", self.name)
        label = changes.get("label", self.label)
        value = changes.get("value", self.value)
        response = cast(
            MetricResponse,
            self._request(
                self.api_requests_registry.metrics.upsert_metric(
                    experiment_id=experiment_id,
                    name=name,
                    value=value,
                    label=label,
                )
            ),
        )
        self._hydrate(response)

    def delete(self) -> None:
        """Delete the metric on the server and block later local updates."""
        self._ensure_not_deleted()
        self._request(self.api_requests_registry.metrics.delete_metric(self.id))
        self._deleted = True
