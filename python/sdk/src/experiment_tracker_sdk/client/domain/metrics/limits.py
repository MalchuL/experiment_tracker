"""Metric API outbound string limits (align with backend metric DTOs)."""

from __future__ import annotations

from experiment_tracker_shared.limits import ENTITY_NAME_MAX_LEN

from experiment_tracker_sdk.utils.text_limits import truncate


def truncate_metric_name(name: str) -> str:
    return truncate(name, ENTITY_NAME_MAX_LEN, field_label="Metric name") or name


def truncate_metric_label(label: str | None) -> str | None:
    return truncate(label, ENTITY_NAME_MAX_LEN, field_label="Metric label")


def truncate_metric_label_query_param(label: str) -> str:
    return truncate(label, ENTITY_NAME_MAX_LEN, field_label="Metric label filter") or label
