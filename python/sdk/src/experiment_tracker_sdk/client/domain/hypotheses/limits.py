"""Hypothesis API outbound string limits (align with backend hypothesis DTOs)."""

from __future__ import annotations

from experiment_tracker_shared.limits import (
    ENTITY_DESCRIPTION_MAX_LEN,
    ENTITY_NAME_MAX_LEN,
)

from experiment_tracker_sdk.utils.text_limits import truncate


def truncate_hypothesis_title(title: str) -> str:
    return truncate(title, ENTITY_NAME_MAX_LEN, field_label="Hypothesis title") or title


def truncate_hypothesis_description(description: str) -> str:
    return (
        truncate(
            description,
            ENTITY_DESCRIPTION_MAX_LEN,
            field_label="Hypothesis description",
        )
        or description
    )


def truncate_hypothesis_author(author: str) -> str:
    return truncate(author, ENTITY_NAME_MAX_LEN, field_label="Hypothesis author") or author


def truncate_hypothesis_baseline(baseline: str) -> str:
    return (
        truncate(baseline, ENTITY_NAME_MAX_LEN, field_label="Hypothesis baseline")
        or baseline
    )


def truncate_hypothesis_target_metric_name(name: str) -> str:
    return (
        truncate(name, ENTITY_NAME_MAX_LEN, field_label="Hypothesis target metric name")
        or name
    )
