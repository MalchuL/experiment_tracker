"""SQLAlchemy column types that keep wall-clock timestamps aligned with UTC storage rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from experiment_tracker_shared.datetime_utc import normalize_for_db


class UtcNaiveDateTime(TypeDecorator[datetime]):
    """Store and load ``datetime`` values as **naive UTC** for ``TIMESTAMP WITHOUT TIME ZONE``.

    PostgreSQL (and similar) ``timestamp without time zone`` does not record a time zone. This
    decorator ensures that anything written through SQLAlchemy is normalized the same way:
    aware datetimes are converted to UTC then stripped to naive; naive values are passed through
    (callers must already mean UTC). That keeps advanced-alchemy and raw inserts from persisting
    ambiguous local-offset values by mistake.

    On read, if the driver ever returns a timezone-aware value, it is normalized the same way so
    application code consistently sees naive UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> datetime | None:
        """Called when a Python value is written to the DB (INSERT/UPDATE bind parameters).

        Args:
            value: Attribute value from the ORM, usually ``datetime`` or ``None``. Non-datetime
                values are returned unchanged so SQLAlchemy can report type errors elsewhere.
            dialect: Active SQLAlchemy dialect (unused; kept for TypeDecorator API).

        Returns:
            ``None`` for SQL NULL, otherwise a **naive** UTC ``datetime`` suitable for the column.
        """
        if value is None:
            return None
        if not isinstance(value, datetime):
            return value  # type: ignore[return-value]
        return normalize_for_db(value)

    def process_result_value(self, value: Any, dialect: Any) -> datetime | None:
        """Called when a row value is read from the DB into Python.

        Args:
            value: Raw value from the driver, usually ``datetime`` or ``None``.
            dialect: Active SQLAlchemy dialect (unused; kept for TypeDecorator API).

        Returns:
            ``None`` for SQL NULL. For ``datetime`` results, returns naive UTC—if the driver
            attached a ``tzinfo``, it is stripped after converting to UTC so code matches bind rules.
        """
        if value is None:
            return None
        if not isinstance(value, datetime):
            return value
        if value.tzinfo is not None:
            return normalize_for_db(value)
        return value
