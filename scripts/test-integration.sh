#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
for tool in docker uv; do
  command -v "$tool" >/dev/null || { echo "Required command missing: $tool" >&2; exit 1; }
done
docker info >/dev/null
docker compose version >/dev/null

export INTEGRATION_BACKEND_PORT=${INTEGRATION_BACKEND_PORT:-18000}
export INTEGRATION_WEB_PORT=${INTEGRATION_WEB_PORT:-13000}
export INTEGRATION_SCALARS_PORT=${INTEGRATION_SCALARS_PORT:-18001}
export INTEGRATION_STORAGE_PORT=${INTEGRATION_STORAGE_PORT:-18002}
export INTEGRATION_API_URL="http://127.0.0.1:$INTEGRATION_BACKEND_PORT/api"
export INTEGRATION_WEB_URL="http://127.0.0.1:$INTEGRATION_WEB_PORT"
export INTEGRATION_SCALARS_URL="http://127.0.0.1:$INTEGRATION_SCALARS_PORT/api"
export INTEGRATION_STORAGE_URL="http://127.0.0.1:$INTEGRATION_STORAGE_PORT/api"
export INTEGRATION_ADMIN_KEY=integration-admin
export INTEGRATION_RESULTS_DIR="$repo_dir/.integration-results/$(date -u +%Y%m%dT%H%M%S)-$$"
mkdir -p "$INTEGRATION_RESULTS_DIR"
compose=(docker compose --env-file /dev/null -p "tracker-integration-$$" -f "$repo_dir/python/integration/compose.yml")
cleanup() {
  status=$?
  trap - EXIT
  "${compose[@]}" logs --no-color >"$INTEGRATION_RESULTS_DIR/services.log" 2>&1 || true
  "${compose[@]}" down --volumes --remove-orphans >"$INTEGRATION_RESULTS_DIR/teardown.log" 2>&1 || status=1
  echo "Integration results: $INTEGRATION_RESULTS_DIR"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cd "$repo_dir/python/integration"
uv sync --locked
# Install Linux system prerequisites once with: uv run playwright install-deps chromium
uv run playwright install chromium
"${compose[@]}" up --build --detach --wait --wait-timeout 300 2>&1 | tee "$INTEGRATION_RESULTS_DIR/startup.log"
uv run python wait_ready.py
uv run pytest "$@" --browser chromium --tracing retain-on-failure --screenshot only-on-failure \
  --output "$INTEGRATION_RESULTS_DIR/browser" --junitxml "$INTEGRATION_RESULTS_DIR/junit.xml" \
  2>&1 | tee "$INTEGRATION_RESULTS_DIR/pytest.log"
