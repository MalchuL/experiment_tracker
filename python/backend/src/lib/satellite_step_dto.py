"""Shared DTO for one optional satellite call outcome (object storage or scalars)."""

from __future__ import annotations

from pydantic import BaseModel

from lib.dto_config import model_config
from lib.satellite_deletion import SatelliteCallResult


class SatelliteStepDTO(BaseModel):
    """One satellite HTTP call outcome for delete/teardown responses."""

    ok: bool
    skipped: bool = False
    error_message: str | None = None

    model_config = model_config()


def satellite_step_from_result(result: SatelliteCallResult) -> SatelliteStepDTO:
    """Normalize ``run_satellite`` outcome for API responses (ok / skipped / error text)."""
    return SatelliteStepDTO(
        ok=result.ok,
        skipped=result.skipped,
        error_message=result.error_message,
    )
