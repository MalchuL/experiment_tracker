"""SQLAlchemy types for UTC-naive timestamps."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from experiment_tracker_shared.datetime_utc import normalize_for_db


class UtcNaiveDateTime(TypeDecorator[datetime]):
    """Persist datetimes as naive UTC; normalize aware values on bind."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            return value  # type: ignore[return-value]
        return normalize_for_db(value)

    def process_result_value(self, value: Any, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            return value
        if value.tzinfo is not None:
            return normalize_for_db(value)
        return value
