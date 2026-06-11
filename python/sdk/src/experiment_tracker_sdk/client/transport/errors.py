"""Shared HTTP error handling and request payload normalization."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from experiment_tracker_sdk.client.utils import log_error_response
from experiment_tracker_sdk.logger import logger


def raise_for_status(response: httpx.Response, suppress_errors: bool) -> None:
    """Call ``response.raise_for_status()`` and log failures.

    When ``suppress_errors`` is ``True`` (client ``supress_errors`` flag), HTTP
    errors are logged but not re-raised.
    """
    try:
        response.raise_for_status()
    except Exception:  # noqa: BLE001
        log_error_response(response, logger)
        if not suppress_errors:
            raise


def convert_payload_to_json(
    payload: dict[str, Any] | BaseModel | None,
) -> dict[str, Any] | None:
    """Normalize ``ApiRequestSpec.request_payload`` to a JSON-serializable dict."""
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json", exclude_unset=True)
    return payload
