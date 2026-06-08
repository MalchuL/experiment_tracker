# Build from repo root: docker compose -f docker-compose.dev.yml build backend
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /build/python/backend
ENV UV_LINK_MODE=copy
COPY python/shared /build/python/shared
COPY python/backend /build/python/backend
WORKDIR /build/python/backend
RUN uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 wget \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build/python/backend
COPY --from=builder /build/python /build/python
COPY python/backend/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV UV_LINK_MODE=copy
RUN rm -rf /build/python/backend/.venv \
    && cd /build/python/backend && /bin/uv sync --frozen --no-dev
ENV PATH="/build/python/backend/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=8 \
    CMD wget -qO- http://127.0.0.1:8000/openapi.json >/dev/null 2>&1 || exit 1
ENTRYPOINT ["/entrypoint.sh"]
