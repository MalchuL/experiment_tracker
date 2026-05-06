"""Pydantic helpers so this service's JSON datetimes match JS ``Date.toISOString()`` (UTC ``Z``).

See :mod:`experiment_tracker_shared.datetime_utc` for the canonical formatting implementation.
This module only wires that format into Pydantic's JSON serialization path.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from experiment_tracker_shared.datetime_utc import to_json_utc_z
from pydantic import PlainSerializer


def serialize_required_utc_datetime_for_json(value: datetime) -> str:
    """Serialize a non-null ``datetime`` for JSON output as ISO-8601 UTC with a ``Z`` suffix.

    Args:
        value: Instant to send on the wire. Naive datetimes are interpreted as UTC; aware values
            are shifted to UTC before formatting.

    Returns:
        Timestamp string suitable for ``JSON.parse`` / ``Date`` in browsers, e.g.
        ``2026-05-01T14:30:00Z`` or with fractional seconds as produced by ``to_json_utc_z``.
    """
    return to_json_utc_z(value)


ApiDateTime = Annotated[
    datetime,
    PlainSerializer(
        serialize_required_utc_datetime_for_json,
        return_type=str,
        when_used="json",
    ),
]
