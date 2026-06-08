"""Configure the asynchronous SQLAlchemy engine and request sessions."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mltools.config.settings import get_settings
from mltools.db.models import Base

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables() -> None:
    """Create missing MLTools tables from ORM metadata.

    Returns:
        None: The schema initialization transaction is committed before returning.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield one request-scoped async database session.

    Yields:
        AsyncSession: Session closed automatically after the consuming request ends.
    """
    async with session_maker() as session:
        yield session
"""Async SQLAlchemy engine, session factory, and FastAPI database dependencies."""
