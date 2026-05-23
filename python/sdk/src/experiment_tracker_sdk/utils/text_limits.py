"""Shared low-level string truncation for SDK outbound payloads."""

from __future__ import annotations

from experiment_tracker_sdk.logger import logger


def truncate(value: str | None, max_len: int, *, field_label: str) -> str | None:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    logger.warning(
        "%s exceeded max length (%d) and was truncated.",
        field_label,
        max_len,
    )
    return value[:max_len]
