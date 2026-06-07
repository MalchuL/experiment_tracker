"""Strict recursive normalization for hyperparameter payloads."""

from __future__ import annotations

import math
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from experiment_tracker_sdk.error import HparamsSerializationError


def _fail(path: str, detail: str) -> HparamsSerializationError:
    return HparamsSerializationError(
        f'Failed to serialize hyperparameters. Key "{path}" {detail}.'
    )


def _numpy_scalar(value: Any) -> bool:
    try:
        import numpy as np  # type: ignore[import-not-found]
    except ImportError:
        return False
    generic = getattr(np, "generic", None)
    return generic is not None and isinstance(value, generic)


def _normalize(value: Any, path: str, active: set[int]) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _fail(path, "contains a non-finite float")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return _normalize(value.value, path, active)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if _numpy_scalar(value):
        return _normalize(value.item(), path, active)

    if isinstance(value, dict):
        identity = id(value)
        if identity in active:
            raise _fail(path, "contains a reference cycle")
        active.add(identity)
        try:
            normalized: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise _fail(path, f'contains non-string dictionary key {key!r}')
                child_path = f"{path}.{key}" if path else key
                normalized[key] = _normalize(item, child_path, active)
            return normalized
        finally:
            active.remove(identity)

    if isinstance(value, list):
        identity = id(value)
        if identity in active:
            raise _fail(path, "contains a reference cycle")
        active.add(identity)
        try:
            return [
                _normalize(item, f"{path}[{index}]", active)
                for index, item in enumerate(value)
            ]
        finally:
            active.remove(identity)

    raise _fail(path, f'contains unsupported type "{type(value).__name__}"')


def serialize_hparams(hparams: dict[str, Any]) -> dict[str, Any]:
    """Return a strict JSON-compatible full replacement hparams document."""

    if not isinstance(hparams, dict):
        raise HparamsSerializationError(
            "Failed to serialize hyperparameters. Expected a dictionary."
        )
    return _normalize(hparams, "", set())
