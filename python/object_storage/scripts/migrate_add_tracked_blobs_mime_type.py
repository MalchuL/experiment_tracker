from __future__ import annotations

import asyncio

import sqlalchemy as sa
from sqlalchemy import text

from object_storage.db.database import engine


async def main() -> None:
    """Add ``tracked_blobs.mime_type`` when the storage database needs it.

    Args:
        None. The script uses the configured object-storage SQLAlchemy engine.

    Returns:
        None. It prints a status message and mutates the database schema only
        when the table exists and the column is missing.
    """
    async with engine.begin() as conn:
        exists = await conn.run_sync(_tracked_blobs_exists)
        if not exists:
            print("tracked_blobs table does not exist; nothing to migrate")
            return

        has_column = await conn.run_sync(_has_mime_type_column)
        if has_column:
            print("tracked_blobs.mime_type already exists")
            return

        await conn.execute(
            text(
                "ALTER TABLE tracked_blobs "
                "ADD COLUMN mime_type VARCHAR(255) "
                "NOT NULL DEFAULT 'application/octet-stream'"
            )
        )
        print("added tracked_blobs.mime_type")


def _tracked_blobs_exists(connection: sa.Connection) -> bool:
    """Check whether the target table exists before applying the migration.

    Args:
        connection: Synchronous SQLAlchemy connection supplied by
            ``AsyncConnection.run_sync``.

    Returns:
        ``True`` when the ``tracked_blobs`` table exists, otherwise ``False``.
    """
    return "tracked_blobs" in sa.inspect(connection).get_table_names()


def _has_mime_type_column(connection: sa.Connection) -> bool:
    """Check whether ``tracked_blobs`` already has a MIME type column.

    Args:
        connection: Synchronous SQLAlchemy connection supplied by
            ``AsyncConnection.run_sync``.

    Returns:
        ``True`` when a ``mime_type`` column is present, otherwise ``False``.
    """
    columns = sa.inspect(connection).get_columns("tracked_blobs")
    return any(column["name"] == "mime_type" for column in columns)


if __name__ == "__main__":
    asyncio.run(main())
