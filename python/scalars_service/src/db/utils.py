from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def build_async_database_url(url: str) -> str:
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please set DATABASE_URL to a valid QuestDB connection string. "
            "Example: DATABASE_URL='questdb://admin:quest@localhost:8812/qdb'"
        )

    if url.startswith("questdb://"):
        url = url.replace("questdb://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    new_query = urlencode(
        {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
    )

    new_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )

    return new_url


def build_async_asyncpg_url(url: str) -> str:
    """Builds an asyncpg URL from a QuestDB URL.
    Usefull to connect to QuestDB using asyncpg (For example, to create tables in database).
    Args:
        url (str): QuestDB URL

    Returns:
        str: Asyncpg URL
    """
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please set DATABASE_URL to a valid QuestDB connection string. "
            "Example: DATABASE_URL='questdb://admin:quest@localhost:8812/qdb'"
        )

    # Because QuestDB uses PostgreSQL protocol, we need to convert the URL to PostgreSQL URL
    if url.startswith("questdb://"):
        url = url.replace("questdb://", "postgresql://", 1)

    _ = urlparse(url)

    return url
