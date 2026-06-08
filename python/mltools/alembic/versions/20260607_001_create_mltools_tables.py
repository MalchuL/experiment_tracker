"""Create MLTools hyperparameter importance tables.

Revision ID: 20260607_001
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "20260607_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial MLTools job, result, artifact, and message tables.

    Args:
        None.

    Returns:
        None after the schema objects represented by the ORM metadata exist.
    """
    # Keep the migration aligned with the ORM while allowing SQLite-based local use.
    from mltools.db.models import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Remove every schema object introduced by the initial MLTools migration.

    Args:
        None.

    Returns:
        None after all tables represented by the ORM metadata are removed.
    """
    from mltools.db.models import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
