"""Unit tests for hparam flattening, inference, and importance aggregation."""

import numpy as np

from mltools.domain.hparam_importance.analysis import (
    aggregate_importance,
    flat_key,
    flatten_hparams,
    infer_type,
)


def test_flatten_hparams_handles_nested_arrays_and_separator_collision() -> None:
    result = flatten_hparams(
        {"optimizer": {"lr": 0.1}, "layers": [16, 32], "a<sep>b": True},
        overrides={"layers": {"array_strategy": "flatten_by_index"}},
    )

    assert result.values["optimizer<sep>lr"] == 0.1
    assert result.values["layers<sep>0"] == 16
    assert result.paths["a\\<sep>b"] == ["a<sep>b"]
    assert any(item.category == "path_separator_collision" for item in result.warnings)


def test_flatten_hparams_skips_or_stringifies_arrays() -> None:
    skipped = flatten_hparams({"layers": [1, 2]})
    stringified = flatten_hparams(
        {"layers": [1, 2]},
        overrides={"layers": {"array_strategy": "stringify_category"}},
    )

    assert skipped.values == {}
    assert skipped.warnings[0].category == "unsupported_array"
    assert stringified.values["layers"] == "[1,2]"


def test_type_inference() -> None:
    assert infer_type([1, 2.0, None]) == "number"
    assert infer_type([True, False]) == "boolean"
    assert infer_type(["2026-06-07", "2026-06-08"]) == "date"
    assert infer_type(["2026-06-07T10:00:00Z"]) == "datetime"
    assert infer_type(["adamw", "sgd"]) == "category"
    assert infer_type(["x" * 300]) == "text"


def test_flat_key_is_reversible_through_path_mapping() -> None:
    key, collision = flat_key(["a<sep>b", r"c\d"], "<sep>")
    assert key == r"a\<sep>b<sep>c\\d"
    assert collision is True


def test_aggregate_importance_sums_encoded_columns() -> None:
    class Transformer:
        """Minimal transformer exposing sklearn-compatible output slices."""

        output_indices_ = {"f0": slice(0, 2), "f1": slice(2, 3)}

    result = aggregate_importance(
        Transformer(),  # type: ignore[arg-type]
        np.array([0.2, 0.3, 0.5]),
        [{"flat_key": "category"}, {"flat_key": "number"}],
    )
    assert result == {"category": 0.5, "number": 0.5}
