from __future__ import annotations

from abc import ABC
import re
from typing import Any, Literal, overload
from uuid import UUID

from pydantic import BaseModel

from experiment_tracker_sdk.api_access import ExpTrackerApiAccess
from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.error import ExpTrackerAPIError

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6,8}$")


@overload
def validate_uuid(
    value: str | UUID | None,
    *,
    field_name: str,
    required: Literal[True],
) -> str: ...


@overload
def validate_uuid(
    value: str | UUID | None,
    *,
    field_name: str,
    required: Literal[False] = False,
) -> str | None: ...


def validate_uuid(
    value: str | UUID | None,
    *,
    field_name: str,
    required: bool = False,
) -> str | None:
    """Validate and normalize an id value to a canonical string.

    Args:
        value: Candidate UUID value.
        field_name: Field label used in error messages.
        required: When ``True``, ``None`` is rejected before validation.

    Returns:
        Canonical UUID string, or ``None`` when ``value`` is ``None`` and
        ``required`` is ``False``.

    Raises:
        ValueError: If ``value`` is not a valid UUID.
    """
    if value is None:
        if required:
            raise ValueError(f"{field_name} must be a valid UUID")
        return None
    if isinstance(value, UUID):
        return str(value)
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid UUID") from exc


def validate_hex_color(value: object) -> str | None:
    """Validate an optional ``#RRGGBB`` or ``#RRGGBBAA`` hex color string.

    Args:
        value: Candidate color value, or ``None`` to clear the color.

    Returns:
        The original color string, or ``None``.

    Raises:
        ValueError: If ``value`` is not ``None`` and is not a hex color in
            ``#RRGGBB`` or ``#RRGGBBAA`` format.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("color must be a HEX color in #RRGGBB or #RRGGBBAA format")
    if not HEX_COLOR_RE.fullmatch(value):
        raise ValueError("color must be a HEX color in #RRGGBB or #RRGGBBAA format")
    return value


def resolve_client_and_registry(
    request_client: ExperimentTrackerClient | None = None,
    api_requests_registry: APIRequestsRegistry | None = None,
) -> tuple[ExperimentTrackerClient, APIRequestsRegistry]:
    """Resolve SDK request dependencies for instances and builders.

    Args:
        request_client: Optional explicit SDK HTTP client. When omitted, the
            process-wide :class:`ExpTrackerApiAccess` client is used.
        api_requests_registry: Optional explicit request-spec registry. When
            omitted, the process-wide :class:`ExpTrackerApiAccess` registry is
            used.

    Returns:
        A tuple of ``(request_client, api_requests_registry)`` that is safe for
        issuing typed SDK requests.
    """
    access = ExpTrackerApiAccess.instance()
    return (
        request_client or access.get_request_client(),
        api_requests_registry or access.get_api_requests_registry(),
    )


class ServerInstance(ABC):
    """Base class for SDK objects backed by server rows.

    Instances represent one server-side object and provide a common lifecycle:
    fetch or create a DTO, hydrate local read/write properties from it, push
    updates immediately on property assignment, or batch updates inside a
    context manager until clean exit.

    Args:
        request_client: Optional SDK HTTP client used to execute request specs.
            Supplying this is useful in tests and for callers that manage their
            own client lifetime.
        api_requests_registry: Optional registry of request-spec factories.
            Supplying this is useful in tests and for callers that need a custom
            registry.

    Attributes:
        _mutable_fields: Field names that subclasses allow property setters to
            update on the server. Subclasses define this as a class-level
            ``frozenset``.
        _request_client: Resolved SDK HTTP client used for all server writes,
            fetches, and deletes.
        _api_requests_registry: Resolved request-spec registry used to build
            typed SDK requests.
        _in_context: ``True`` while inside ``with instance:``. Setters record
            dirty fields instead of pushing immediately while this is true.
        _deleted: ``True`` after ``delete()`` succeeds. Any later update attempt
            raises :class:`ExpTrackerAPIError`.
        _dirty: Pending field changes collected during a context manager block.
            On clean exit these are sent as one update request.
        _context_originals: Original values for fields changed inside a context.
            If the context exits with an exception, these values are restored and
            no update request is sent.
    """

    _mutable_fields: frozenset[str] = frozenset()

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
        self._in_context = False
        self._deleted = False
        self._dirty: dict[str, Any] = {}
        self._context_originals: dict[str, Any] = {}

    @property
    def api_requests_registry(self) -> APIRequestsRegistry:
        """Request-spec registry bound to this instance."""
        return self._api_requests_registry

    @property
    def request_client(self) -> ExperimentTrackerClient:
        """SDK HTTP client bound to this instance."""
        return self._request_client

    def __enter__(self):
        """Enter batched update mode for property assignments.

        Returns:
            The instance itself, with clean pending-change buffers.
        """
        self._ensure_not_deleted()
        # Context mode batches property updates until ``__exit__``.
        self._in_context = True
        self._dirty.clear()
        self._context_originals.clear()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[exit-return]
        """Leave batched update mode and optionally push queued changes.

        Args:
            exc_type: Exception type raised inside the context, or ``None`` on a
                clean exit.
            exc: Exception instance raised inside the context, or ``None``.
            tb: Traceback for the exception raised inside the context, or
                ``None``.

        Returns:
            ``False`` so exceptions are never suppressed.
        """
        self._in_context = False
        if exc_type is not None:
            # Keep the local object aligned with the server when no update is sent.
            for field_name, value in self._context_originals.items():
                self._assign_field(field_name, value)
            self._dirty.clear()
            self._context_originals.clear()
            return False
        if self._dirty:
            self._push_update(dict(self._dirty))
            self._dirty.clear()
        self._context_originals.clear()
        return False

    def _ensure_not_deleted(self) -> None:
        """Raise if the instance has already been deleted on the server.

        Raises:
            ExpTrackerAPIError: If ``delete()`` has completed for this instance.
        """
        if self._deleted:
            raise ExpTrackerAPIError(f"{type(self).__name__} has been deleted")

    def _set_mutable_field(self, field_name: str, value: Any) -> None:
        """Assign one mutable field and push or queue the server update.

        Args:
            field_name: Public DTO field name to update, for example ``name`` or
                ``description``.
            value: New local value for the field.

        Raises:
            ExpTrackerAPIError: If the instance has been deleted.
            AttributeError: If ``field_name`` is not listed in the subclass
                ``_mutable_fields`` set.
        """
        self._ensure_not_deleted()
        if field_name not in self._mutable_fields:
            raise AttributeError(f"{field_name} is not mutable")
        if self._in_context and field_name not in self._context_originals:
            # Store the first value seen in this context so exception rollback is stable.
            self._context_originals[field_name] = getattr(self, f"_{field_name}")
        self._assign_field(field_name, value)
        if self._in_context:
            self._dirty[field_name] = value
            return
        self._push_update({field_name: value})

    def _assign_field(self, field_name: str, value: Any) -> None:
        """Set an internal backing attribute without triggering server updates.

        Args:
            field_name: Public DTO field name. The value is stored on the
                instance as ``_{field_name}``.
            value: Value to store locally.
        """
        object.__setattr__(self, f"_{field_name}", value)

    def _hydrate(self, response: BaseModel) -> None:
        """Copy all fields from a Pydantic response DTO into local state.

        Args:
            response: DTO returned by a server request. Field names are copied as
                private backing attributes such as ``_id`` and ``_name``.
        """
        for field_name in type(response).model_fields:
            self._assign_field(field_name, getattr(response, field_name))

    def _request(self, spec):
        """Execute one SDK request spec through the resolved request client.

        Args:
            spec: :class:`ApiRequestSpec` built by the registry.

        Returns:
            Parsed response returned by ``ExperimentTrackerClient.request``.
        """
        return self._request_client.request(spec)

    def _push_update(self, changes: dict[str, Any]) -> None:
        """Push pending field changes to the server.

        Args:
            changes: Mapping of mutable field names to their new values.

        Subclasses implement this method because each domain object maps changes
        to a different request-spec factory.
        """
        raise NotImplementedError

    def delete(self) -> None:
        """Delete this server object.

        Subclasses implement the concrete delete request and mark the instance
        deleted after the server accepts it.
        """
        raise NotImplementedError
