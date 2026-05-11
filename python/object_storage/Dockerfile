# Build from repo root: docker compose build object-storage
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /build/python/object_storage
ENV UV_LINK_MODE=copy
COPY python/shared /build/python/shared
COPY python/object_storage /build/python/object_storage
WORKDIR /build/python/object_storage
RUN uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 ca-certificates wget \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build/python/object_storage
COPY --from=builder /build/python /build/python
ENV UV_LINK_MODE=copy
RUN rm -rf /build/python/object_storage/.venv \
    && cd /build/python/object_storage && /bin/uv sync --frozen --no-dev
ENV PATH="/build/python/object_storage/.venv/bin:$PATH"
EXPOSE 8002
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD wget -qO- http://127.0.0.1:8002/openapi.json >/dev/null 2>&1 || exit 1
CMD ["uvicorn", "object_storage.main:app", "--host", "0.0.0.0", "--port", "8002"]
