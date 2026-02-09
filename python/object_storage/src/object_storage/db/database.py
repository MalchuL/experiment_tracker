from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from object_storage.config import get_settings
from object_storage.db.models import Base

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session tied to the CAS metadata store."""

    async with AsyncSessionLocal() as session:
        yield session


async def create_db_and_tables() -> None:
    """Create metadata tables for CAS experiments, snapshots, and blobs."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
