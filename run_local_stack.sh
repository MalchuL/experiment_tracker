#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

launch_terminal() {
  local title="$1"
  local run_cmd="$2"
  local wrapped_cmd="cd \"$ROOT_DIR\" && $run_cmd; echo; echo \"[$title] exited. Press Enter to close.\"; read -r"

  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -lc "$wrapped_cmd"
    return
  fi

  if command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -T "$title" -e bash -lc "$wrapped_cmd"
    return
  fi

  if command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -lc "$wrapped_cmd"
    return
  fi

  echo "No supported terminal emulator found."
  echo "Install gnome-terminal (recommended), x-terminal-emulator, or xterm."
  exit 1
}

POSTGRES_BACKEND_PORT="${POSTGRES_BACKEND_PORT:-5435}"
POSTGRES_OBJECT_STORAGE_PORT="${POSTGRES_OBJECT_STORAGE_PORT:-5434}"
POSTGRES_USER="${POSTGRES_USER:-tracker}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-tracker}"
POSTGRES_DB="${POSTGRES_DB:-experiment_tracker}"
POSTGRES_OBJECT_STORAGE_DB="${POSTGRES_OBJECT_STORAGE_DB:-object_storage}"

BACKEND_DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_BACKEND_PORT}/${POSTGRES_DB}}"
OBJECT_STORAGE_DATABASE_URL="${OBJECT_STORAGE_DATABASE_URL:-postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_OBJECT_STORAGE_PORT}/${POSTGRES_OBJECT_STORAGE_DB}}"

wait_for_postgres() {
  local container="$1"
  local tries=30
  while (( tries-- > 0 )); do
    if docker exec "$container" pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Timed out waiting for $container" >&2
  exit 1
}

ensure_env_file() {
  local dir="$1"
  if [[ -f "${dir}/.env" ]]; then
    return 0
  fi
  if [[ ! -f "${dir}/.env.example" ]]; then
    echo "Missing ${dir}/.env.example" >&2
    exit 1
  fi
  cp "${dir}/.env.example" "${dir}/.env"
  echo "Created ${dir}/.env from .env.example"
}

ensure_env_file "${ROOT_DIR}/python/backend"
ensure_env_file "${ROOT_DIR}/python/scalars_service"
ensure_env_file "${ROOT_DIR}/python/object_storage"

echo "Starting PostgreSQL via docker run (backend :${POSTGRES_BACKEND_PORT}, object storage :${POSTGRES_OBJECT_STORAGE_PORT})…"
docker rm -f postgres-backend postgres-object-storage >/dev/null 2>&1 || true

docker run -d \
  --name postgres-backend \
  -p "${POSTGRES_BACKEND_PORT}:5432" \
  -v "${ROOT_DIR}/storage/postgres-backend:/var/lib/postgresql/data" \
  -e "POSTGRES_USER=${POSTGRES_USER}" \
  -e "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" \
  -e "POSTGRES_DB=${POSTGRES_DB}" \
  postgres:16-alpine

docker run -d \
  --name postgres-object-storage \
  -p "${POSTGRES_OBJECT_STORAGE_PORT}:5432" \
  -v "${ROOT_DIR}/storage/postgres-object-storage:/var/lib/postgresql/data" \
  -e "POSTGRES_USER=${POSTGRES_USER}" \
  -e "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" \
  -e "POSTGRES_DB=${POSTGRES_OBJECT_STORAGE_DB}" \
  postgres:16-alpine

wait_for_postgres postgres-backend
wait_for_postgres postgres-object-storage

# Object storage: MinIO
launch_terminal \
  "local-run: minio" \
  "cd python/object_storage && docker rm -f minio >/dev/null 2>&1 || true; docker run -p 9000:9000 -p 9001:9001 --name minio -v minio:/data -e \"MINIO_ROOT_USER=admin\" -e \"MINIO_ROOT_PASSWORD=password\" minio/minio server /data --console-address \":9001\""
sleep 2

# Object storage service
launch_terminal \
  "local-run: object-storage" \
  "cd python/object_storage && export DATABASE_URL=\"${OBJECT_STORAGE_DATABASE_URL}\" && uv run uvicorn object_storage.main:app --reload --port 8002 --log-level debug"
sleep 2

# Scalars: ClickHouse
launch_terminal \
  "local-run: clickhouse" \
  "docker rm -f clickhouse-server >/dev/null 2>&1 || true; docker run --name clickhouse-server --ulimit nofile=262144:262144 -p 8123:8123 -e CLICKHOUSE_USER=default -e CLICKHOUSE_PASSWORD=yourpass -e CLICKHOUSE_DB=metrics -v ./.clickhouse_data:/var/lib/clickhouse/ clickhouse/clickhouse-server"
sleep 2

# Scalars service
launch_terminal \
  "local-run: scalars-service" \
  "cd python/scalars_service && uv run uvicorn api.main:app --reload --port 8001 --log-level debug"
sleep 2

# Backend
launch_terminal \
  "local-run: backend" \
  "cd python/backend && export DATABASE_URL=\"${BACKEND_DATABASE_URL}\" && uv run uvicorn api.main:app --reload --port 8000 --log-level debug"
sleep 2

# Frontend
launch_terminal \
  "local-run: frontend" \
  "cd apps/web && export PUBLIC_API_BASE_URL=\"${PUBLIC_API_BASE_URL:-http://127.0.0.1:8000}\" && pnpm run dev"

echo "Launched local stack in separate terminal windows."
