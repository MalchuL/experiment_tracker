"""add experiment tags

Revision ID: dea9cb85cdf3
Revises: 20260218_01
Create Date: 2026-02-19 00:08:55.747847

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "dea9cb85cdf3"
down_revision = "20260218_01"
branch_labels = None
depends_on = None

DB_VERSION = "2026.02.19.01"


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO db_metadata (id, version)
            VALUES (1, :version)
            ON CONFLICT (id) DO UPDATE SET version = EXCLUDED.version
            """
        ),
        {"version": DB_VERSION},
    )


def downgrade() -> None:
    op.drop_column("experiments", "tags")
