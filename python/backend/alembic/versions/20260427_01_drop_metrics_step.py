"""Drop step column from metrics (use created_at for ordering).

Revision ID: 20260427_01
Revises: 20260304_01
Create Date: 2026-04-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260427_01"
down_revision: Union[str, Sequence[str], None] = "20260304_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DB_VERSION = "2026.04.27.01"


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


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "metrics" in table_names:
        metric_columns = {column["name"] for column in inspector.get_columns("metrics")}
        if "step" in metric_columns:
            with op.batch_alter_table("metrics", schema=None) as batch_op:
                batch_op.drop_column("step")

    if "db_metadata" in table_names:
        _upsert_db_version(DB_VERSION)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "metrics" in table_names:
        metric_columns = {column["name"] for column in inspector.get_columns("metrics")}
        if "step" not in metric_columns:
            with op.batch_alter_table("metrics", schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "step",
                        sa.Integer(),
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )

    if "db_metadata" in table_names:
        _upsert_db_version("2026.03.04.01")
