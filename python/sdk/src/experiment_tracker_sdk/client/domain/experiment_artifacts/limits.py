"""Experiment artifact multipart / query outbound string limits."""

from __future__ import annotations

import json

from experiment_tracker_shared.limits import ENTITY_NAME_MAX_LEN

from experiment_tracker_sdk.utils.text_limits import truncate


def truncate_artifact_logical_name(name: str) -> str:
    return truncate(name, ENTITY_NAME_MAX_LEN, field_label="Artifact name") or name


def truncate_experiment_tags_json(tags: list[str] | None) -> str | None:
    """JSON array string for multipart ``tags`` after per-tag truncation."""
    if tags is None:
        return None
    truncated = [
        truncate(t, ENTITY_NAME_MAX_LEN, field_label="Artifact log tag") or t
        for t in tags
    ]
    return json.dumps(truncated)
