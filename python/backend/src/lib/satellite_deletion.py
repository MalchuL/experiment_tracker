"""Helpers for optional satellite-service calls (object storage, scalars) during deletion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable


@dataclass(slots=True)
class SatelliteCallResult:
    """Structured result from ``run_satellite`` so callers never need bare try/except.

    Attributes:
        ok: ``True`` when the awaitable completed without raising (or call was skipped).
        skipped: ``True`` when no client was configured (``None`` awaitable) or similar.
        error_message: Populated when ``ok`` is ``False`` because the coroutine raised.
        detail: Optional structured payload from the satellite (often a Pydantic ``BaseModel``)
            on success.
    """

    ok: bool
    skipped: bool = False
    error_message: str | None = None
    detail: Any = None


async def run_satellite(awaitable: Awaitable[Any] | None) -> SatelliteCallResult:
    """Await a satellite client coroutine, capturing errors instead of propagating.

    Used for **optional** dependencies: object storage or scalars URLs may be unset in dev,
    or the remote may be temporarily unavailable. Callers translate ``SatelliteCallResult``
    into DTO fields (``SatelliteStepDTO``) or merge ``detail`` dicts (usage).

    Args:
        awaitable: Coroutine returned by a client method, or ``None`` to mean "skip".

    Returns:
        ``SatelliteCallResult`` with ``ok``/``skipped``/``error_message``/``detail`` filled
        appropriately; never raises for ordinary HTTP/client failures inside ``awaitable``.
    """
    if awaitable is None:
        return SatelliteCallResult(ok=True, skipped=True)
    try:
        detail = await awaitable
        return SatelliteCallResult(ok=True, skipped=False, detail=detail)
    except Exception as exc:  # noqa: BLE001 — surface to caller as structured outcome
        return SatelliteCallResult(ok=False, skipped=False, error_message=str(exc))
