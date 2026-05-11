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

# Production-like local stack: no uvicorn --reload; Next.js is built then `next start`.
export NEXT_PUBLIC_BASE_URL="${NEXT_PUBLIC_BASE_URL:-http://127.0.0.1:8000}"

echo "Building apps/web (production)…"
(
  cd "$ROOT_DIR/apps/web"
  pnpm run build
)

# Object storage: MinIO
launch_terminal \
  "local-run: minio" \
  "cd python/object_storage && docker rm -f minio >/dev/null 2>&1 || true; docker run -p 9000:9000 -p 9001:9001 --name minio -v minio:/data -e \"MINIO_ROOT_USER=admin\" -e \"MINIO_ROOT_PASSWORD=password\" minio/minio server /data --console-address \":9001\""
sleep 2

# Object storage service
launch_terminal \
  "local-run: object-storage" \
  "cd python/object_storage && uv run uvicorn object_storage.main:app --port 8002 --log-level debug"
sleep 2

# Scalars: ClickHouse
launch_terminal \
  "local-run: clickhouse" \
  "docker rm -f clickhouse-server >/dev/null 2>&1 || true; docker run --name clickhouse-server --ulimit nofile=262144:262144 -p 8123:8123 -e CLICKHOUSE_USER=default -e CLICKHOUSE_PASSWORD=yourpass -e CLICKHOUSE_DB=metrics -v ./.clickhouse_data:/var/lib/clickhouse/ clickhouse/clickhouse-server"
sleep 2

# Scalars service
launch_terminal \
  "local-run: scalars-service" \
  "cd python/scalars_service && uv run uvicorn api.main:app --port 8001 --log-level debug"
sleep 2

# Backend
launch_terminal \
  "local-run: backend" \
  "cd python/backend && uv run uvicorn api.main:app --port 8000 --log-level debug"
sleep 2

# Frontend (built app)
launch_terminal \
  "local-run: frontend (production)" \
  "cd apps/web && export NEXT_PUBLIC_BASE_URL=\"$NEXT_PUBLIC_BASE_URL\" && pnpm run start"

echo "Launched local stack in separate terminal windows."
