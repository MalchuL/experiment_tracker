"""JSON-safe wire encoding for scalar metric values (finite, NaN, ±inf)."""

from __future__ import annotations

import math
from typing import Literal

ScalarSpecial = Literal["nan", "inf", "-inf"]
ScalarWireValue = float | ScalarSpecial
ScalarValueKind = Literal["finite", "nan", "inf", "-inf"]

_SCALAR_SPECIAL_TO_FLOAT: dict[ScalarSpecial, float] = {
    "nan": math.nan,
    "inf": math.inf,
    "-inf": -math.inf,
}


def scalar_to_wire(value: float) -> ScalarWireValue:
    """Encode a Python float for JSON-safe scalar APIs."""
    if math.isnan(value):
        return "nan"
    if value == math.inf:
        return "inf"
    if value == -math.inf:
        return "-inf"
    return value


def scalar_from_wire(value: ScalarWireValue) -> float:
    """Decode a wire scalar value to a native Python float."""
    if isinstance(value, str):
        return _SCALAR_SPECIAL_TO_FLOAT[value]
    return float(value)


def classify_scalar_wire(value: ScalarWireValue) -> ScalarValueKind:
    """Classify a wire scalar value."""
    if isinstance(value, str):
        return value
    if math.isnan(value):
        return "nan"
    if value == math.inf:
        return "inf"
    if value == -math.inf:
        return "-inf"
    return "finite"
