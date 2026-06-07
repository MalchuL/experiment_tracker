from __future__ import annotations

import math
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

import pytest

from experiment_tracker_sdk.error import HparamsSerializationError
from experiment_tracker_sdk.hparams import serialize_hparams


class Optimizer(Enum):
    ADAMW = "adamw"


def test_serialize_hparams_converts_supported_values() -> None:
    result = serialize_hparams(
        {
            "path": Path("runs/model.pt"),
            "optimizer": Optimizer.ADAMW,
            "date": date(2026, 6, 7),
            "time": datetime(2026, 6, 7, 12, tzinfo=timezone.utc),
            "nested": {"values": [1, True, None, 0.5]},
        }
    )

    assert result == {
        "path": "runs/model.pt",
        "optimizer": "adamw",
        "date": "2026-06-07",
        "time": "2026-06-07T12:00:00+00:00",
        "nested": {"values": [1, True, None, 0.5]},
    }


def test_serialize_hparams_converts_numpy_scalar_when_installed() -> None:
    np = pytest.importorskip("numpy")

    assert serialize_hparams({"batch_size": np.int64(32)}) == {"batch_size": 32}


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_serialize_hparams_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(HparamsSerializationError, match="optimizer.lr"):
        serialize_hparams({"optimizer": {"lr": value}})


def test_serialize_hparams_rejects_unsupported_type_with_path() -> None:
    with pytest.raises(HparamsSerializationError, match="optimizer.custom"):
        serialize_hparams({"optimizer": {"custom": object()}})


def test_serialize_hparams_rejects_non_string_keys() -> None:
    with pytest.raises(HparamsSerializationError, match="non-string dictionary key"):
        serialize_hparams({"nested": {1: "value"}})  # type: ignore[dict-item]


def test_serialize_hparams_rejects_cycles() -> None:
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic

    with pytest.raises(HparamsSerializationError, match="reference cycle"):
        serialize_hparams(cyclic)
