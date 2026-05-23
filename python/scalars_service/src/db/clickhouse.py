from typing import Optional, TypedDict
from urllib.parse import urlparse

from clickhouse_connect import get_async_client
from clickhouse_connect.driver.asyncclient import AsyncClient
from config import get_settings  # type: ignore


class ClickHouseConnectionParams(TypedDict):
    host: str
    port: int
    username: str
    password: str
    database: str
    secure: bool


_clickhouse_client: Optional[AsyncClient] = None


def _parse_clickhouse_url(url: str) -> ClickHouseConnectionParams:
    if not url:
        raise RuntimeError(
            "CLICKHOUSE_URL environment variable is not set. "
            "Please set CLICKHOUSE_URL to a valid ClickHouse connection string. "
            "Example: CLICKHOUSE_URL='http://default:@localhost:8123/default'"
        )

    if "://" not in url:
        url = f"http://{url}"

    parsed = urlparse(url)
    secure = parsed.scheme in {"https", "clickhouses"}

    host = parsed.hostname or "localhost"
    port = parsed.port or (8443 if secure else 8123)
    username = parsed.username or "default"
    password = parsed.password or ""
    database = parsed.path.lstrip("/") or "default"

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "database": database,
        "secure": secure,
    }


async def init_clickhouse_client() -> AsyncClient:
    """Create the shared process-wide ClickHouse client (idempotent)."""
    global _clickhouse_client
    if _clickhouse_client is None:
        params = _parse_clickhouse_url(get_settings().CLICKHOUSE_URL)
        _clickhouse_client = await get_async_client(**params)
    return _clickhouse_client


async def close_clickhouse_client() -> None:
    """Close and clear the shared ClickHouse client."""
    global _clickhouse_client
    if _clickhouse_client is not None:
        await _clickhouse_client.close()
        _clickhouse_client = None


async def get_clickhouse_client() -> AsyncClient:
    """FastAPI dependency: return the shared ClickHouse client."""
    return await init_clickhouse_client()


async def check_connection() -> None:
    try:
        client = await init_clickhouse_client()
        await client.command("SELECT 1")
    except Exception as e:
        await close_clickhouse_client()
        raise RuntimeError(
            f"Failed to connect to ClickHouse at {get_settings().CLICKHOUSE_URL}. "
            f"Please ensure the database exists and is accessible. Error: {e}"
        ) from e
