"""Enforce one metric per (experiment, name, label) for upsert semantics.

Revision ID: 20260428_01
Revises: 20260427_01
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260428_01"
down_revision: Union[str, Sequence[str], None] = "20260427_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DB_VERSION = "2026.04.28.01"


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


def _dedupe_metrics_table() -> None:
    """Keep the newest row (by created_at) per (experiment, name, label) key."""
    op.execute(
        sa.text(
            """
            DELETE FROM metrics
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY experiment_id, name, label
                        ORDER BY created_at DESC, id DESC
                    ) AS rn
                    FROM metrics
                    WHERE label IS NOT NULL
                ) t
                WHERE rn > 1
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM metrics
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY experiment_id, name
                        ORDER BY created_at DESC, id DESC
                    ) AS rn
                    FROM metrics
                    WHERE label IS NULL
                ) t
                WHERE rn > 1
            )
            """
        )
    )


def _create_unique_indexes() -> None:
    op.create_index(
        "uq_metrics_experiment_name_label",
        "metrics",
        ["experiment_id", "name", "label"],
        unique=True,
        postgresql_where=sa.text("label IS NOT NULL"),
        sqlite_where=sa.text("label IS NOT NULL"),
    )
    op.create_index(
        "uq_metrics_experiment_name_unlabeled",
        "metrics",
        ["experiment_id", "name"],
        unique=True,
        postgresql_where=sa.text("label IS NULL"),
        sqlite_where=sa.text("label IS NULL"),
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "metrics" not in inspector.get_table_names():
        return

    existing = {i["name"] for i in inspector.get_indexes("metrics")}

    if (
        "uq_metrics_experiment_name_label" in existing
        and "uq_metrics_experiment_name_unlabeled" in existing
    ):
        if "db_metadata" in inspector.get_table_names():
            _upsert_db_version(DB_VERSION)
        return

    if bind.dialect.name in {"postgresql", "sqlite"}:
        _dedupe_metrics_table()
        if "uq_metrics_experiment_name_label" not in existing:
            _create_unique_indexes()

    if "db_metadata" in inspector.get_table_names():
        _upsert_db_version(DB_VERSION)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "metrics" not in inspector.get_table_names():
        return
    for name in (
        "uq_metrics_experiment_name_unlabeled",
        "uq_metrics_experiment_name_label",
    ):
        if name in {i["name"] for i in inspector.get_indexes("metrics")}:
            op.drop_index(name, table_name="metrics")
    if "db_metadata" in inspector.get_table_names():
        _upsert_db_version("2026.04.27.01")
