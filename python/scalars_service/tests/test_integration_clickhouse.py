"""Integration tests against isolated ClickHouse container."""

from __future__ import annotations

from uuid import uuid4

import pytest
from clickhouse_connect import get_async_client
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_clickhouse_connection(clickhouse_url: str) -> None:
    """Verify ClickHouse container is reachable."""
    from urllib.parse import urlparse

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
        result = await client.query("SELECT 1")
        assert result.result_rows == [(1,)]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_projects_create_and_exists(clickhouse_url: str) -> None:
    """Create project table via API and verify existence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        project_id = uuid4()
        create_resp = await client.post(
            "/api/projects",
            json={"project_id": str(project_id)},
        )
        assert create_resp.status_code == 200

        exists_resp = await client.get(f"/api/projects/exists/{project_id}")
        assert exists_resp.status_code == 200
        assert exists_resp.json()["exists"] is True
