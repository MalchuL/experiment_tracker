"""Replace empty experiment feature objects with arrays.

Revision ID: 20260518_001
Revises: None
Create Date: 2026-05-18

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260518_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                """
                UPDATE experiments
                SET features = '[]'::jsonb
                WHERE features = '{}'::jsonb
                """
            )
        )
        return

    bind.execute(
        sa.text(
            """
            UPDATE experiments
            SET features = '[]'
            WHERE features = '{}'
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                """
                UPDATE experiments
                SET features = '{}'::jsonb
                WHERE features = '[]'::jsonb
                """
            )
        )
        return

    bind.execute(
        sa.text(
            """
            UPDATE experiments
            SET features = '{}'
            WHERE features = '[]'
            """
        )
    )
