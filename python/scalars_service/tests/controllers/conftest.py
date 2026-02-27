"""Controller test fixtures."""

from __future__ import annotations

from urllib.parse import urlparse

import pytest
from clickhouse_connect import get_async_client
from httpx import ASGITransport, AsyncClient

from api.main import app
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS


@pytest.fixture
async def ensure_mapping_table(clickhouse_url: str) -> None:
    """Create the mapping table (normally done in app lifespan)."""
    parsed = urlparse(clickhouse_url)
    host = parsed.hostname or "localhost"
    port = int(parsed.port or 8123)
    user = parsed.username or "default"
    password = parsed.password or ""
    database = parsed.path.lstrip("/") or "default"

    client = await get_async_client(
        host=host,
        port=port,
        username=user,
        password=password,
        database=database,
        secure=False,
    )
    try:
        await client.command(SCALARS_DB_UTILS.build_create_mapping_table_statement())
    finally:
        await client.close()


@pytest.fixture
async def http_client(ensure_mapping_table: None) -> AsyncClient:
    """HTTP client for controller tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
