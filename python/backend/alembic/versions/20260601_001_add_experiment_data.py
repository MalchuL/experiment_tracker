"""Add experiment data table.

Revision ID: 20260601_001
Revises: 20260518_001
Create Date: 2026-06-01

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260601_001"
down_revision = "20260518_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the ``experiment_data`` storage table and supporting enum/index.

    Args:
        None. Alembic supplies the active migration connection through
        ``op.get_bind()``.

    Returns:
        None. The function mutates the database schema in place.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        data_type = postgresql.ENUM(
            "snapshot", name="experiment_data_type", create_type=True
        )
        data_type.create(bind, checkfirst=True)
        json_type = postgresql.JSONB(astext_type=sa.Text())
    else:
        data_type = sa.Enum("snapshot", name="experiment_data_type")
        json_type = sa.JSON()

    op.create_table(
        "experiment_data",
        sa.Column("experiment_id", sa.UUID(), nullable=False),
        sa.Column("type", data_type, nullable=False),
        sa.Column("data", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["experiments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "experiment_id", "type", name="uq_experiment_data_experiment_type"
        ),
    )
    op.create_index(
        "ix_experiment_data_experiment_type",
        "experiment_data",
        ["experiment_id", "type"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the ``experiment_data`` schema objects created by ``upgrade``.

    Args:
        None. Alembic supplies the active migration connection through
        ``op.get_bind()``.

    Returns:
        None. The function removes the index, table, and PostgreSQL enum when
        the active dialect owns a concrete enum type.
    """
    op.drop_index("ix_experiment_data_experiment_type", table_name="experiment_data")
    op.drop_table("experiment_data")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(name="experiment_data_type").drop(bind, checkfirst=True)
