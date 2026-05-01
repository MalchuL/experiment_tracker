"""Pydantic types: JSON-serialize datetimes as ISO-8601 UTC with ``Z``."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from experiment_tracker_shared.datetime_utc import to_json_utc_z
from pydantic import PlainSerializer


def _ser_dt(v: datetime) -> str:
    return to_json_utc_z(v)


def _ser_dt_opt(v: datetime | None) -> str | None:
    if v is None:
        return None
    return to_json_utc_z(v)


ApiDateTime = Annotated[
    datetime,
    PlainSerializer(_ser_dt, return_type=str, when_used="json"),
]

ApiOptionalDateTime = Annotated[
    datetime | None,
    PlainSerializer(_ser_dt_opt, return_type=str | None, when_used="json"),
]
