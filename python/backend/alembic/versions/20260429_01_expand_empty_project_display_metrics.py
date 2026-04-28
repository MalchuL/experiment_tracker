"""Expand empty project display_metrics to explicit tracked keys.

Legacy: `displayMetrics` / `display_metrics` == [] meant “show all tracked” in the UI.
After this migration, [] means “none”; rows that meant “all” store an explicit list.

Revision ID: 20260429_01
Revises: 20260428_01
Create Date: 2026-04-29 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260429_01"
down_revision: Union[str, Sequence[str], None] = "20260428_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DB_VERSION = "2026.04.29.01"


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


def _tracked_item_to_display_key(tracked: dict[str, Any]) -> str | dict[str, Any]:
    name = tracked.get("name")
    label = tracked.get("label")
    if label is None or label == "":
        return name if isinstance(name, str) else str(name)
    return {"name": name, "label": label}


def _maybe_expand_metrics(metrics: Any) -> tuple[Any, bool]:
    if not isinstance(metrics, dict):
        return metrics, False
    tracked = metrics.get("tracked_metrics") or metrics.get("trackedMetrics") or []
    display = metrics.get("display_metrics") or metrics.get("displayMetrics") or []
    if not isinstance(tracked, list) or not isinstance(display, list):
        return metrics, False
    if len(tracked) == 0 or len(display) > 0:
        return metrics, False
    new_display = [_tracked_item_to_display_key(t) for t in tracked if isinstance(t, dict)]
    out = dict(metrics)
    if "displayMetrics" in metrics:
        out["displayMetrics"] = new_display
    elif "display_metrics" in metrics:
        out["display_metrics"] = new_display
    else:
        out["displayMetrics"] = new_display
    return out, True


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "projects" not in set(inspector.get_table_names()):
        if "db_metadata" in inspector.get_table_names():
            _upsert_db_version(DB_VERSION)
        return

    rows = bind.execute(sa.text("SELECT id, metrics FROM projects")).fetchall()
    projects_table = sa.table(
        "projects",
        sa.column("id", sa.String),
        sa.column("metrics", postgresql.JSONB),
    )
    for row in rows:
        new_metrics, changed = _maybe_expand_metrics(row.metrics)
        if changed:
            bind.execute(
                projects_table.update()
                .where(projects_table.c.id == row.id)
                .values(metrics=new_metrics)
            )

    if "db_metadata" in inspector.get_table_names():
        _upsert_db_version(DB_VERSION)


def downgrade() -> None:
    """Lossy: clears explicit display lists that match “expanded from empty” pattern."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "projects" not in set(inspector.get_table_names()):
        return

    rows = bind.execute(sa.text("SELECT id, metrics FROM projects")).fetchall()
    projects_table = sa.table(
        "projects",
        sa.column("id", sa.String),
        sa.column("metrics", postgresql.JSONB),
    )
    for row in rows:
        m = row.metrics
        if not isinstance(m, dict):
            continue
        tracked = m.get("tracked_metrics") or m.get("trackedMetrics") or []
        display = m.get("display_metrics") or m.get("displayMetrics") or []
        if not isinstance(tracked, list) or not isinstance(display, list):
            continue
        if len(tracked) == 0 or len(display) == 0:
            continue
        expected = [_tracked_item_to_display_key(t) for t in tracked if isinstance(t, dict)]
        if display == expected:
            out = dict(m)
            if "displayMetrics" in m:
                out["displayMetrics"] = []
            elif "display_metrics" in m:
                out["display_metrics"] = []
            else:
                out["displayMetrics"] = []
            bind.execute(
                projects_table.update()
                .where(projects_table.c.id == row.id)
                .values(metrics=out)
            )

    if "db_metadata" in inspector.get_table_names():
        _upsert_db_version("2026.04.28.01")
