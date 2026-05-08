"""Add lifecycle active flags, nullable owners, and ON DELETE SET NULL on owner FKs.

- ``is_active`` on ``teams``, ``projects``, ``experiments`` (default true).
- ``projects.owner_id`` and ``teams.owner_id``: nullable, FK to ``users.id`` with ``ON DELETE SET NULL``.

Revision ID: 20260503_01
Revises: 20260429_01
Create Date: 2026-05-03 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260503_01"
down_revision: Union[str, Sequence[str], None] = "20260429_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DB_VERSION = "2026.05.03.01"


def _upsert_db_version(version: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "db_metadata" not in inspector.get_table_names():
        return
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


def _add_is_active(table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if "is_active" in columns:
        return
    op.add_column(
        table_name,
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column(table_name, "is_active", server_default=None)


def _projects_owner_fk_name(inspector: sa.Inspector) -> str | None:
    if "projects" not in inspector.get_table_names():
        return None
    for fk in inspector.get_foreign_keys("projects"):
        if fk.get("constrained_columns") == ["owner_id"] and fk.get("referred_table") == "users":
            return fk.get("name")
    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in ("teams", "projects", "experiments"):
        _add_is_active(table_name)
    if "projects" in inspector.get_table_names():
        fk_name = _projects_owner_fk_name(inspector)
        if fk_name:
            op.drop_constraint(fk_name, "projects", type_="foreignkey")
        op.create_foreign_key(
            "projects_owner_id_fkey",
            "projects",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.alter_column("projects", "owner_id", nullable=True)
    if "teams" in inspector.get_table_names():
        op.drop_constraint("teams_owner_id_fkey", "teams", type_="foreignkey")
        op.create_foreign_key(
            "teams_owner_id_fkey",
            "teams",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.alter_column("teams", "owner_id", nullable=True)
    _upsert_db_version(DB_VERSION)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "projects" in inspector.get_table_names():
        op.alter_column("projects", "owner_id", nullable=False)
        fk_name = _projects_owner_fk_name(inspector)
        if fk_name:
            op.drop_constraint(fk_name, "projects", type_="foreignkey")
        op.create_foreign_key(
            "projects_owner_id_fkey",
            "projects",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if "teams" in inspector.get_table_names():
        op.alter_column("teams", "owner_id", nullable=False)
        op.drop_constraint("teams_owner_id_fkey", "teams", type_="foreignkey")
        op.create_foreign_key(
            "teams_owner_id_fkey",
            "teams",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )
    for table_name in ("experiments", "projects", "teams"):
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "is_active" in columns:
            op.drop_column(table_name, "is_active")
    _upsert_db_version("2026.04.29.01")
