"""Experiment API outbound string limits (align with backend experiment row columns)."""

from __future__ import annotations

from experiment_tracker_shared.limits import (
    ENTITY_DESCRIPTION_MAX_LEN,
    ENTITY_NAME_MAX_LEN,
)

from experiment_tracker_sdk.utils.text_limits import truncate


def truncate_experiment_name(name: str) -> str:
    return truncate(name, ENTITY_NAME_MAX_LEN, field_label="Experiment name") or name


def truncate_experiment_description(description: str) -> str:
    return (
        truncate(
            description,
            ENTITY_DESCRIPTION_MAX_LEN,
            field_label="Experiment description",
        )
        or description
    )
