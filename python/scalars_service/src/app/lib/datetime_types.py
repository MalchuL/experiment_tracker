"""Pydantic helpers so scalars service JSON datetimes use UTC with a trailing ``Z``.

Delegates formatting to ``experiment_tracker_shared.datetime_utc.to_json_utc_z`` so this service
stays aligned with the main API and JavaScript ``toISOString()`` conventions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from experiment_tracker_shared.datetime_utc import to_json_utc_z
from pydantic import PlainSerializer


def serialize_required_utc_datetime_for_json(value: datetime) -> str:
    """Serialize a ``datetime`` for JSON as ISO-8601 UTC ending with ``Z``.

    Args:
        value: Clock reading to encode. Naive values follow the project rule (UTC wall clock);
            timezone-aware values are normalized to UTC first.

    Returns:
        A string safe to parse in the UI with ``Date`` / ``parseISO`` (UTC ``Z`` form).
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
