"""Add metric label and db metadata versioning.

Revision ID: 20260218_01
Revises:
Create Date: 2026-02-18 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260218_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DB_VERSION = "2026.02.18.01"


def _upsert_db_version(version: str) -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect in {"postgresql", "sqlite"}:
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
        return

    result = bind.execute(
        sa.text("UPDATE db_metadata SET version = :version WHERE id = 1"),
        {"version": version},
    )
    if result.rowcount == 0:
        bind.execute(
            sa.text("INSERT INTO db_metadata (id, version) VALUES (1, :version)"),
            {"version": version},
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "metrics" in table_names:
        metric_columns = {column["name"] for column in inspector.get_columns("metrics")}
        with op.batch_alter_table("metrics", schema=None) as batch_op:
            if "label" not in metric_columns:
                batch_op.add_column(sa.Column("label", sa.String(length=100), nullable=True))
            if "direction" in metric_columns:
                batch_op.drop_column("direction")

        if bind.dialect.name == "postgresql":
            op.execute(sa.text("DROP TYPE IF EXISTS metricdirection"))

    if "db_metadata" not in table_names:
        op.create_table(
            "db_metadata",
            sa.Column("id", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("version", sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    _upsert_db_version(DB_VERSION)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "metrics" in table_names:
        metric_columns = {column["name"] for column in inspector.get_columns("metrics")}
        with op.batch_alter_table("metrics", schema=None) as batch_op:
            if "direction" not in metric_columns:
                batch_op.add_column(
                    sa.Column(
                        "direction",
                        sa.Enum("MINIMIZE", "MAXIMIZE", name="metricdirection"),
                        nullable=False,
                        server_default="MINIMIZE",
                    )
                )
            if "label" in metric_columns:
                batch_op.drop_column("label")

    if "db_metadata" in table_names:
        op.drop_table("db_metadata")
