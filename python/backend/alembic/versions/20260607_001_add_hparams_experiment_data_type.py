"""Add hparams experiment-data type.

Revision ID: 20260607_001
Revises: 20260601_001
Create Date: 2026-06-07
"""

from __future__ import annotations

from alembic import op

revision = "20260607_001"
down_revision = "20260601_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE experiment_data_type ADD VALUE IF NOT EXISTS 'hparams'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be safely removed while rows may reference them.
    pass
