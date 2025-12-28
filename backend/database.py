import os
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base, User


def build_async_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please set DATABASE_URL to a valid PostgreSQL connection string. "
            "Example: DATABASE_URL='postgresql://username:password@localhost:5432/experiment_tracker'"
        )
    
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    query_params.pop("sslmode", None)
    
    new_query = urlencode({k: v[0] if len(v) == 1 else v for k, v in query_params.items()})
    
    new_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    return new_url


DATABASE_URL = build_async_database_url()

try:
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
except Exception as e:
    raise RuntimeError(
        f"Failed to connect to database at {DATABASE_URL}. "
        f"Please ensure the database exists and is accessible. Error: {e}"
    ) from e


async def create_db_and_tables():
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_maker:
        async with async_session_maker() as session:
            yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
