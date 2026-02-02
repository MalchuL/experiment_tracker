from typing import AsyncGenerator

import asyncpg
from config import get_settings
from .utils import build_async_database_url, build_async_asyncpg_url
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


DATABASE_URL = build_async_database_url(get_settings().QUEST_DB_URL)

try:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
except Exception as e:
    raise RuntimeError(
        f"Failed to connect to database at {DATABASE_URL}. "
        f"Please ensure the database exists and is accessible. Error: {e}"
    ) from e


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_maker:
        async with async_session_maker() as session:
            yield session


async def get_asyncpg_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    conn = await asyncpg.connect(build_async_asyncpg_url(get_settings().QUEST_DB_URL))
    yield conn


async def check_connection():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(
            f"Failed to connect to database at {DATABASE_URL}. "
            f"Please ensure the database exists and is accessible. Error: {e}"
        ) from e
