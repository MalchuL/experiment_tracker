from __future__ import annotations

import time
from urllib.request import urlopen

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.postgres import PostgresContainer

from object_storage.config import get_settings


def _to_asyncpg_url(database_url: str) -> str:
    """Convert a sync SQLAlchemy/Postgres URL to asyncpg URL."""

    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def _wait_minio_ready(endpoint_url: str, timeout_s: float = 30.0) -> None:
    """Wait until MinIO responds on health endpoint."""

    ready_url = f"{endpoint_url.rstrip('/')}/minio/health/ready"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(ready_url) as response:  # noqa: S310
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
            continue
    raise RuntimeError(f"MinIO did not become ready in {timeout_s}s: {ready_url}")


@pytest.fixture(scope="session", autouse=True)
def isolated_test_environment(pytestconfig: pytest.Config) -> None:
    """
    Start isolated Postgres/MinIO containers and expose config via env vars.

    This keeps test data out of developer local services and avoids overlap.
    """

    postgres = PostgresContainer("postgres:16-alpine")
    minio = DockerContainer("minio/minio:latest")
    minio.with_exposed_ports(9000)
    minio.with_env("MINIO_ROOT_USER", "admin")
    minio.with_env("MINIO_ROOT_PASSWORD", "password")
    minio.with_command('server /data --console-address ":9001"')

    try:
        postgres.start()
        minio.start()
    except Exception as exc:
        pytest.skip(f"Docker/testcontainers unavailable: {exc}")
        return

    db_url = _to_asyncpg_url(postgres.get_connection_url())
    minio_host = minio.get_container_host_ip()
    minio_port = minio.get_exposed_port(9000)
    endpoint_url = f"http://{minio_host}:{minio_port}"
    _wait_minio_ready(endpoint_url)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_ENDPOINT_URL", endpoint_url)
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "admin")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "password")
    monkeypatch.setenv("S3_BUCKET", "ml-blobs-test")

    # Make current worker's dynamic env visible for tests that need paths.
    pytestconfig.cache.set("object_storage/test_database_url", db_url)
    pytestconfig.cache.set("object_storage/test_s3_endpoint_url", endpoint_url)

    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()
        monkeypatch.undo()
        minio.stop()
        postgres.stop()


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """Ensure tests do not leak cached settings across env changes."""

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
