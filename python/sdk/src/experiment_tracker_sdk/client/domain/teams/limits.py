"""Team API outbound string limits (align with backend team DTOs)."""

from __future__ import annotations

from experiment_tracker_shared.limits import (
    ENTITY_DESCRIPTION_MAX_LEN,
    ENTITY_NAME_MAX_LEN,
)

from experiment_tracker_sdk.utils.text_limits import truncate


def truncate_team_name(name: str) -> str:
    return truncate(name, ENTITY_NAME_MAX_LEN, field_label="Team name") or name


def truncate_team_description(description: str | None) -> str | None:
    return truncate(
        description,
        ENTITY_DESCRIPTION_MAX_LEN,
        field_label="Team description",
    )
