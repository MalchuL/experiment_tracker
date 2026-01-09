import os
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from config.settings import get_settings
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import Base, User
from db.utils import build_async_database_url

DATABASE_URL = build_async_database_url(get_settings().database_url)

try:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
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
