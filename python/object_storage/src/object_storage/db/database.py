from collections.abc import AsyncGenerator

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from object_storage.config import get_settings
from object_storage.db.models import Base

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def _ensure_snapshots_project_id(connection: Connection) -> None:
    """Align legacy ``snapshots`` rows with the ORM (``project_id``).

    Older schemas used ``experiment_id``; ``create_all`` does not add columns to existing
    tables, so production DBs can miss ``project_id`` entirely.
    """
    insp = sa.inspect(connection)
    if "snapshots" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("snapshots")}
    if "project_id" in cols:
        return
    dialect = connection.dialect.name
    if dialect != "postgresql":
        return
    if "experiment_id" in cols:
        connection.execute(text("ALTER TABLE snapshots ADD COLUMN project_id UUID"))
        connection.execute(text("UPDATE snapshots SET project_id = experiment_id"))
        connection.execute(
            text("ALTER TABLE snapshots ALTER COLUMN project_id SET NOT NULL")
        )
        connection.execute(text("ALTER TABLE snapshots DROP COLUMN experiment_id"))
    else:
        # Cannot infer project for legacy rows; current API is project-scoped only.
        connection.execute(text("DELETE FROM snapshots"))
        connection.execute(
            text("ALTER TABLE snapshots ADD COLUMN project_id UUID NOT NULL")
        )
    connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_snapshots_project_id ON snapshots (project_id)"
        )
    )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session tied to the CAS metadata store."""

    async with AsyncSessionLocal() as session:
        yield session


async def create_db_and_tables() -> None:
    """Create metadata tables for CAS experiments, snapshots, and blobs."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_snapshots_project_id)
