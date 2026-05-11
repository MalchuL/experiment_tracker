from typing import AsyncGenerator

from config.settings import get_settings
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import Base, User
from db.utils import build_async_database_url

# Bump when the ORM schema in ``models.py`` changes in a breaking way.
APPLICATION_SCHEMA_VERSION = "1"

DATABASE_URL = build_async_database_url(get_settings().database_url)


def _ensure_db_metadata_row(connection) -> None:
    """Ensure ``db_metadata`` has the canonical row (``id = 1``)."""
    from sqlalchemy import inspect, text

    insp = inspect(connection)
    if "db_metadata" not in insp.get_table_names():
        return
    if connection.execute(text("SELECT 1 FROM db_metadata WHERE id = 1")).first() is not None:
        return
    connection.execute(
        text("INSERT INTO db_metadata (id, version) VALUES (1, :version)"),
        {"version": APPLICATION_SCHEMA_VERSION},
    )

try:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
except Exception as e:
    raise RuntimeError(
        f"Failed to connect to database at {DATABASE_URL}. "
        f"Please ensure the database exists and is accessible. Error: {e}"
    ) from e


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_db_metadata_row)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_maker:
        async with async_session_maker() as session:
            yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
