# Build from repo root: docker compose build scalars
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /build/python/scalars_service
ENV UV_LINK_MODE=copy
COPY python/shared /build/python/shared
COPY python/scalars_service /build/python/scalars_service
WORKDIR /build/python/scalars_service
RUN uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm
# Venv from the builder targets the uv image’s Python; recreate it here so `uvicorn` shebangs match this runtime (see uv Docker guide).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates wget \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build/python/scalars_service
COPY --from=builder /build/python /build/python
ENV UV_LINK_MODE=copy
RUN rm -rf /build/python/scalars_service/.venv \
    && cd /build/python/scalars_service && /bin/uv sync --frozen --no-dev
ENV PATH="/build/python/scalars_service/.venv/bin:$PATH"
ENV PYTHONPATH=/build/python/scalars_service/src
EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=5s --start-period=40s --retries=5 \
    CMD wget -qO- http://127.0.0.1:8001/ >/dev/null 2>&1 || exit 1
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
