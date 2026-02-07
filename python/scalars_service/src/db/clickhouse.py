from typing import AsyncGenerator, TypedDict
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


async def get_clickhouse_client() -> AsyncGenerator[AsyncClient, None]:
    params = _parse_clickhouse_url(get_settings().CLICKHOUSE_URL)
    client = await get_async_client(**params)
    try:
        yield client
    finally:
        await client.close()


async def check_connection() -> None:
    params = _parse_clickhouse_url(get_settings().CLICKHOUSE_URL)
    client = await get_async_client(**params)
    try:
        await client.command("SELECT 1")
    except Exception as e:
        raise RuntimeError(
            f"Failed to connect to ClickHouse at {get_settings().CLICKHOUSE_URL}. "
            f"Please ensure the database exists and is accessible. Error: {e}"
        ) from e
    finally:
        await client.close()
