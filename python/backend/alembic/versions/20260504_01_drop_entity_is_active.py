"""Drop is_active from teams, projects, and experiments.

Revision ID: 20260504_01
Revises: 20260503_01
Create Date: 2026-05-04 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260504_01"
down_revision: Union[str, Sequence[str], None] = "20260503_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("experiments", "is_active")
    op.drop_column("projects", "is_active")
    op.drop_column("teams", "is_active")


def downgrade() -> None:
    op.add_column(
        "teams",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "experiments",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.alter_column("teams", "is_active", server_default=None)
    op.alter_column("projects", "is_active", server_default=None)
    op.alter_column("experiments", "is_active", server_default=None)
