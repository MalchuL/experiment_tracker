"""Pydantic helpers so API JSON encodes datetimes like JavaScript ``Date.toISOString()`` (UTC with ``Z``).

FastAPI/Pydantic default JSON encoding for ``datetime`` often yields ``+00:00`` for aware values or
no ``Z`` suffix for naive values. These ``Annotated`` aliases attach a serializer that runs only
when building JSON (``when_used="json"``), so Python models still use real ``datetime`` objects
while wire payloads stay consistent for browsers and OpenAPI clients.

The actual string format is implemented in ``experiment_tracker_shared.datetime_utc.to_json_utc_z``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from experiment_tracker_shared.datetime_utc import to_json_utc_z
from pydantic import PlainSerializer


def serialize_required_utc_datetime_for_json(value: datetime) -> str:
    """Convert a required ``datetime`` field to a JSON string for API responses.

    Used as Pydantic's ``PlainSerializer`` so ``model_dump(mode="json")`` and FastAPI responses emit
    a single, URL- and JS-friendly form: ISO-8601 in UTC with a trailing ``Z`` (never ``+00:00``).

    Args:
        value: Non-null instant. Naive values are treated as UTC wall clock (same convention as
            database columns using ``UtcNaiveDateTime``). Aware values are converted to UTC first.

    Returns:
        RFC 3339-style timestamp ending with ``Z``, e.g. ``2026-05-01T14:30:00.123456Z``.
    """
    return to_json_utc_z(value)


def serialize_optional_utc_datetime_for_json(value: datetime | None) -> str | None:
    """Convert an optional ``datetime`` field to JSON, preserving null for absent instants.

    Same formatting rules as :func:`serialize_required_utc_datetime_for_json` when ``value`` is
    not ``None``. For optional API fields (e.g. ``started_at``), JSON must emit ``null`` rather than
    an empty string so clients distinguish "not set" from "set to epoch".

    Args:
        value: Instant to serialize, or ``None`` if the field is unset.

    Returns:
        ``None`` when ``value`` is ``None``; otherwise the same ``Z``-suffixed string as the
        required serializer.
    """
    if value is None:
        return None
    return to_json_utc_z(value)


ApiDateTime = Annotated[
    datetime,
    PlainSerializer(
        serialize_required_utc_datetime_for_json,
        return_type=str,
        when_used="json",
    ),
]

ApiOptionalDateTime = Annotated[
    datetime | None,
    PlainSerializer(
        serialize_optional_utc_datetime_for_json,
        return_type=str | None,
        when_used="json",
    ),
]
