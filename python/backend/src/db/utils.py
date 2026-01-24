from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def build_async_database_url(url: str) -> str:
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please set DATABASE_URL to a valid PostgreSQL connection string. "
            "Example: DATABASE_URL='postgresql://username:password@localhost:5432/experiment_tracker'"
        )

    # For SQLite, return as-is without parsing
    if url.startswith("sqlite"):
        return url

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    query_params.pop("sslmode", None)

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
