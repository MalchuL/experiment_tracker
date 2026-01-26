from domain.experiments.error import ExperimentNameParseError
import pytest

from domain.experiments.utils import (
    DEFAULT_EXPERIMENT_NAME_PATTERN,
    parse_experiment_name,
)


def test_parse_experiment_name_default_pattern():
    result = parse_experiment_name(
        "42_from_base_model_change_v2", DEFAULT_EXPERIMENT_NAME_PATTERN
    )

    assert result.num == "42"
    assert result.parent == "base"
    assert result.change == "model_change_v2"


def test_parse_experiment_name_allows_underscores_in_parent_and_change():
    result = parse_experiment_name(
        "7_from_parent_with_underscores_change_with_more_parts",
        DEFAULT_EXPERIMENT_NAME_PATTERN,
    )

    assert result.num == "7"
    assert result.parent == "parent"
    assert result.change == "with_underscores_change_with_more_parts"


def test_parse_experiment_name_missing_fields_defaults_to_empty_strings():
    result = parse_experiment_name("007", "{num}")

    assert result.num == "007"
    assert result.parent == ""
    assert result.change == ""


def test_parse_experiment_name_missing_parent_and_change_defaults_to_empty_strings():
    result = parse_experiment_name(
        "007_change", DEFAULT_EXPERIMENT_NAME_PATTERN, raise_error=False
    )

    assert result.num == ""
    assert result.parent == ""
    assert result.change == "007_change"


def test_concrete_pattern():
    pattern = "{num}_from_{parent}_change_{change}"
    result = parse_experiment_name("42_from_base_model_change_model_change_v2", pattern)
    assert result.num == "42"
    assert result.parent == "base_model"
    assert result.change == "model_change_v2"


def test_with_special_characters():
    pattern = "{num}|{parent}|{change}"
    result = parse_experiment_name("42|base_model|model_change_v2", pattern)
    assert result.num == "42"
    assert result.parent == "base_model"
    assert result.change == "model_change_v2"


def test_parse_experiment_name_raises_on_mismatch():
    with pytest.raises(
        ExperimentNameParseError,
        match="Name 'not_a_match' does not match pattern '{num}_from_{parent}_{change}'",
    ):
        parse_experiment_name("not_a_match", DEFAULT_EXPERIMENT_NAME_PATTERN)
