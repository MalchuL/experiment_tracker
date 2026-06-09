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

# Match the runtime browser API URL used by run_local_stack.sh.
export PUBLIC_API_BASE_URL="${PUBLIC_API_BASE_URL:-http://127.0.0.1:8000}"

echo "Building apps/web (production)…"
(
  cd "$ROOT_DIR/apps/web"
  pnpm run build
)

launch_terminal \
  "local-run: web (production)" \
  "cd apps/web && export PUBLIC_API_BASE_URL=\"$PUBLIC_API_BASE_URL\" && pnpm run start"

echo "Launched production Next.js in a separate terminal window."
