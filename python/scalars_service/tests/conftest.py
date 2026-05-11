"""Pytest fixtures for isolated test environment with testcontainers."""

from __future__ import annotations

import pytest
from testcontainers.clickhouse import ClickHouseContainer

from config import get_settings


@pytest.fixture(scope="session")
def isolated_test_environment(pytestconfig: pytest.Config) -> None:
    """
    Start isolated ClickHouse container and override CLICKHOUSE_URL.

    Keeps test data out of developer local services (per README).
    Only used by tests that request clickhouse_url fixture.
    """
    container = ClickHouseContainer(
        "clickhouse/clickhouse-server:latest",
        username="default",
        password="password",
        dbname="default",
    )

    try:
        container.start()
    except Exception as exc:
        pytest.skip(f"Docker/testcontainers unavailable: {exc}")
        return

    host = container.get_container_host_ip()
    port = container.get_exposed_port(8123)
    url = f"http://default:password@{host}:{port}/default"
    pytestconfig.cache.set("scalars_service/test_clickhouse_url", url)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("CLICKHOUSE_URL", url)

    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()
        monkeypatch.undo()
        container.stop()


@pytest.fixture(scope="session")
def clickhouse_url(isolated_test_environment, pytestconfig: pytest.Config) -> str:
    """Provide ClickHouse URL for integration tests (starts container if needed)."""
    url = pytestconfig.cache.get("scalars_service/test_clickhouse_url", "")
    assert url, "isolated_test_environment should set clickhouse URL"
    return url


@pytest.fixture
async def integration_clickhouse_client(clickhouse_url: str):
    """Async ClickHouse client against ``clickhouse_url`` (isolated testcontainer).

    Ensures the scalar mapping table exists (same as app lifespan / controller tests).
    """
    from urllib.parse import urlparse

    from clickhouse_connect import get_async_client

    from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore

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
        yield client
    finally:
        await client.close()
