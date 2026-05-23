"""Project API outbound string limits (align with backend project row columns)."""

from __future__ import annotations

from experiment_tracker_shared.limits import (
    ENTITY_DESCRIPTION_MAX_LEN,
    ENTITY_NAME_MAX_LEN,
)

from experiment_tracker_sdk.utils.text_limits import truncate


def truncate_project_name(name: str) -> str:
    return truncate(name, ENTITY_NAME_MAX_LEN, field_label="Project name") or name


def truncate_project_description(description: str) -> str:
    return (
        truncate(
            description,
            ENTITY_DESCRIPTION_MAX_LEN,
            field_label="Project description",
        )
        or description
    )
