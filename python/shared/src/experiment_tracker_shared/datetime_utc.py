"""UTC datetime helpers for persistence and JSON (Z-suffixed ISO-8601)."""

from __future__ import annotations

from datetime import datetime

import pendulum


def utc_now_naive() -> datetime:
    """Current instant as naive UTC wall clock (for TIMESTAMP WITHOUT TIME ZONE)."""
    return pendulum.now("UTC").naive()


def normalize_for_db(dt: datetime) -> datetime:
    """Return naive UTC suitable for TIMESTAMP WITHOUT TIME ZONE."""
    if dt.tzinfo is None:
        return dt
    return pendulum.instance(dt).in_tz("UTC").naive()


def to_json_utc_z(dt: datetime) -> str:
    """Serialize instant as ISO-8601 UTC with ``Z`` suffix (not ``+00:00``)."""
    if dt.tzinfo is None:
        p = pendulum.datetime(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.microsecond,
            tz="UTC",
        )
    else:
        p = pendulum.instance(dt).in_tz("UTC")
    s = p.to_iso8601_string()
    if s.endswith("+00:00"):
        return s[:-6] + "Z"
    if s.endswith("Z"):
        return s
    return s + "Z"
