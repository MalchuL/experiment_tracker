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
