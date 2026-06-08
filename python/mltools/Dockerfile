# Build from repo root: docker compose build mltools-api mltools-worker
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /build/python/mltools
ENV UV_LINK_MODE=copy
COPY python/mltools /build/python/mltools
RUN uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 ca-certificates wget \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build/python/mltools
COPY --from=builder /build/python/mltools /build/python/mltools
ENV UV_LINK_MODE=copy
RUN rm -rf .venv && /bin/uv sync --frozen --no-dev
ENV PATH="/build/python/mltools/.venv/bin:$PATH"
ENV PYTHONPATH=/build/python/mltools/src
EXPOSE 8003
HEALTHCHECK --interval=10s --timeout=5s --start-period=40s --retries=5 \
    CMD wget -qO- http://127.0.0.1:8003/openapi.json >/dev/null 2>&1 || exit 1
CMD ["sh", "-c", "alembic upgrade head && uvicorn mltools.api.main:app --host 0.0.0.0 --port 8003"]
