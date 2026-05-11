"""UTC datetime helpers for persistence and JSON (Z-suffixed ISO-8601).

This module is the single source of truth for:

- **"Now"** in the database sense: naive UTC wall clock suitable for ``TIMESTAMP WITHOUT TIME ZONE``.
- **Normalizing** arbitrary ``datetime`` values before write (strip offset after converting to UTC).
- **Formatting** instants for JSON and query strings so they match common JavaScript output
  (``Date.toISOString()``), i.e. UTC with a literal ``Z`` suffix instead of ``+00:00``.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pendulum


def utc_naive_for_clickhouse_insert(dt: datetime) -> datetime:
    """Return a UTC-aware datetime for ``clickhouse-connect`` binary inserts.

    The driver encodes ``DateTime64`` using ``datetime.timestamp()``; **naive** values are
    interpreted as *local* civil time. Values that are UTC wall clock by convention (naive)
    must be tagged as UTC-aware so the encoded POSIX instant matches
    ``toDateTime64(..., 'UTC')`` SQL literals.

    Args:
        dt: Naive UTC wall clock or any aware instant.

    Returns:
        Timezone-aware ``datetime`` in UTC (same instant as ``dt``).
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=timezone.utc)


def utc_now_naive() -> datetime:
    """Return the current instant as a **naive** datetime in the UTC clock.

    PostgreSQL ``timestamp without time zone`` (and similar) store only calendar + clock; they do
    not store a time zone. Callers treat these columns as **UTC by convention**. This function is
    the preferred clock for ``default=`` on ORM columns that follow that rule.

    Returns:
        ``datetime`` with ``tzinfo is None``, representing "now" in UTC (not local server time).
    """
    return pendulum.now("UTC").naive()


def normalize_for_db(dt: datetime) -> datetime:
    """Normalize ``dt`` to naive UTC for columns that store ``TIMESTAMP WITHOUT TIME ZONE`` as UTC.

    SQLAlchemy's :class:`UtcNaiveDateTime` type decorator calls this on bind so aware datetimes from
    clients or libraries are never persisted with a misleading offset: everything is folded to UTC
    and the offset is dropped, matching how the rest of the stack reads these columns.

    Args:
        dt: Any ``datetime``. If ``tzinfo`` is ``None``, the value is returned unchanged (caller
            asserts it is already UTC wall clock). If aware, it is converted to UTC then made
            naive.

    Returns:
        Naive ``datetime`` in the UTC wall clock.
    """
    if dt.tzinfo is None:
        return dt
    return pendulum.instance(dt).in_tz("UTC").naive()


def to_json_utc_z(dt: datetime) -> str:
    """Format an instant as an ISO-8601 / RFC 3339 string in UTC with a trailing ``Z``.

    Intended for HTTP JSON bodies, query parameters, and logs where a single string shape is
    easier for frontends than ``+00:00``. Matches the usual output of JavaScript
    ``new Date(ms).toISOString()`` for the same instant when the instant is UTC.

    Args:
        dt: The instant to format. **Naive** values are interpreted as UTC (same as DB columns).
            **Aware** values are converted to UTC before formatting.

    Returns:
        ISO-8601-like string ending with ``Z``, never ``+00:00`` or a numeric offset. Includes
        fractional seconds when non-zero (via pendulum's string form, then ``Z`` normalization).
    """
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
