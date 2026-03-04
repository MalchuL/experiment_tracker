"""Refactor project metrics/settings JSON contracts.

Revision ID: 20260304_01
Revises: dea9cb85cdf3
Create Date: 2026-03-04 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260304_01"
down_revision: Union[str, Sequence[str], None] = "dea9cb85cdf3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DB_VERSION = "2026.03.04.01"
DEFAULT_NAMING_PATTERN = "{num}_from_{parent}_{change}"


def _upsert_db_version(version: str) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO db_metadata (id, version)
            VALUES (1, :version)
            ON CONFLICT (id) DO UPDATE SET version = EXCLUDED.version
            """
        ),
        {"version": version},
    )


def _normalize_metrics_for_upgrade(metrics: Any, settings: Any) -> dict[str, Any]:
    tracked_metrics: list[Any] = []
    display_metrics: list[str] = []

    if isinstance(metrics, dict):
        tracked_raw = metrics.get("tracked_metrics", metrics.get("trackedMetrics", []))
        display_raw = metrics.get("display_metrics", metrics.get("displayMetrics", []))
        if isinstance(tracked_raw, list):
            tracked_metrics = tracked_raw
        if isinstance(display_raw, list):
            display_metrics = [str(item) for item in display_raw]
    elif isinstance(metrics, list):
        tracked_metrics = metrics

    if not display_metrics and isinstance(settings, dict):
        legacy_display = settings.get("display_metrics", settings.get("displayMetrics", []))
        if isinstance(legacy_display, list):
            display_metrics = [str(item) for item in legacy_display]

    return {
        "tracked_metrics": tracked_metrics,
        "display_metrics": display_metrics,
    }


def _normalize_settings_for_upgrade(settings: Any) -> list[dict[str, Any]]:
    if isinstance(settings, list):
        return settings
    return []


def _normalize_metrics_for_downgrade(metrics: Any) -> list[Any]:
    if isinstance(metrics, list):
        return metrics
    if not isinstance(metrics, dict):
        return []
    tracked_raw = metrics.get("tracked_metrics", metrics.get("trackedMetrics", []))
    if isinstance(tracked_raw, list):
        return tracked_raw
    return []


def _normalize_display_for_downgrade(metrics: Any) -> list[str]:
    if isinstance(metrics, dict):
        display_raw = metrics.get("display_metrics", metrics.get("displayMetrics", []))
        if isinstance(display_raw, list):
            return [str(item) for item in display_raw]
    return []


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "projects" not in set(inspector.get_table_names()):
        _upsert_db_version(DB_VERSION)
        return

    rows = bind.execute(sa.text("SELECT id, metrics, settings FROM projects")).fetchall()
    projects_table = sa.table(
        "projects",
        sa.column("id", sa.String),
        sa.column("metrics", postgresql.JSONB),
        sa.column("settings", postgresql.JSONB),
    )
    for row in rows:
        new_metrics = _normalize_metrics_for_upgrade(row.metrics, row.settings)
        new_settings = _normalize_settings_for_upgrade(row.settings)
        bind.execute(
            projects_table.update()
            .where(projects_table.c.id == row.id)
            .values(metrics=new_metrics, settings=new_settings)
        )

    _upsert_db_version(DB_VERSION)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "projects" not in set(inspector.get_table_names()):
        return

    rows = bind.execute(sa.text("SELECT id, metrics FROM projects")).fetchall()
    projects_table = sa.table(
        "projects",
        sa.column("id", sa.String),
        sa.column("metrics", postgresql.JSONB),
        sa.column("settings", postgresql.JSONB),
    )
    for row in rows:
        legacy_metrics = _normalize_metrics_for_downgrade(row.metrics)
        legacy_settings = {
            "naming_pattern": DEFAULT_NAMING_PATTERN,
            "display_metrics": _normalize_display_for_downgrade(row.metrics),
        }
        bind.execute(
            projects_table.update()
            .where(projects_table.c.id == row.id)
            .values(metrics=legacy_metrics, settings=legacy_settings)
        )
