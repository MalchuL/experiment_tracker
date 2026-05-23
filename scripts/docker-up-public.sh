#!/usr/bin/env bash
# Start the full Compose stack with public UI/API URLs without a root `.env` file.
# Exports ALLOWED_ORIGINS, OBJECT_STORAGE_ALLOWED_ORIGINS, NEXT_PUBLIC_BASE_URL
# (and keeps SERVER_API_BASE_URL=http://backend:8000 for in-network BFF).
#
# Usage:
#   PUBLIC_URL=<ui-origin> ./scripts/docker-up-public.sh [PUBLIC_API_URL] [-- docker compose args...]
#   ./scripts/docker-up-public.sh <ui-origin> [public-api-base] [-- docker compose args...]
#
# If `docker compose` only works with sudo, put assignments after sudo so they reach the script:
#   sudo PUBLIC_URL=http://192.168.1.247 ./scripts/docker-up-public.sh
# Or URL args (no env):   sudo ./scripts/docker-up-public.sh http://192.168.1.247
# Or preserve a prior export:   sudo -E ./scripts/docker-up-public.sh
#
# Examples:
#   PUBLIC_URL=https://dashboard.example.com ./scripts/docker-up-public.sh
#   ./scripts/docker-up-public.sh https://dashboard.example.com https://api.example.com
#   ./scripts/docker-up-public.sh http://myhost:3000
#   PUBLIC_URL=http://192.168.1.247 ./scripts/docker-up-public.sh   # CORS adds :3000 when http has no port
#   WEB_PORT=4000 PUBLIC_URL=http://myhost ./scripts/docker-up-public.sh
#   ./scripts/docker-up-public.sh http://myhost:3000 http://myhost:8000 -- up -d
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "docker-up-public.sh: python3 is required but was not found in PATH" >&2
  exit 1
fi
python3 <<'CHECK'
import sys
if sys.version_info < (3, 8):
    sys.stderr.write(
        "docker-up-public.sh: Python 3.8+ is required (this interpreter is %s)\n"
        % (".".join(map(str, sys.version_info[:3])),)
    )
    raise SystemExit(1)
CHECK

PUBLIC_URL="${PUBLIC_URL:-}"
PUBLIC_API_URL="${PUBLIC_API_URL:-}"
compose_args=(up -d --build)

while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--" ]]; then
    shift
    if [[ $# -eq 0 ]]; then
      echo "Nothing after --; pass docker compose arguments (e.g. -- up -d --build)" >&2
      exit 1
    fi
    compose_args=("$@")
    break
  fi
  if [[ "$1" =~ ^https?:// ]]; then
    if [[ -z "$PUBLIC_URL" ]]; then
      PUBLIC_URL="$1"
    elif [[ -z "$PUBLIC_API_URL" ]]; then
      PUBLIC_API_URL="$1"
    else
      echo "Too many URL arguments. Max two: UI origin, optional API base. Use -- before compose args." >&2
      exit 1
    fi
    shift
    continue
  fi
  echo "Unexpected argument: $1" >&2
  echo "Put docker compose arguments after -- (e.g. $0 https://app.example.com -- up -d)" >&2
  exit 1
done

if [[ -z "$PUBLIC_URL" ]]; then
  cat >&2 <<'EOF'
Set the browser origin of the Next.js UI (scheme + host + port, no path), e.g.:

  PUBLIC_URL=https://tracker.example.com ./scripts/docker-up-public.sh

Or pass it as the first argument:

  ./scripts/docker-up-public.sh https://tracker.example.com [https://api.example.com]

If you omit the second URL, the API base defaults to the same host with port 8000
(http(s)://<host>:8000), matching the default published BACKEND_PORT.

Optional: SERVER_API_BASE_URL (default http://backend:8000) if your Next server
reaches the API differently.

After -- , remaining arguments are passed to `docker compose` (default: up -d --build).
EOF
  exit 1
fi

PUBLIC_URL="${PUBLIC_URL%/}"
if [[ -n "$PUBLIC_API_URL" ]]; then
  PUBLIC_API_URL="${PUBLIC_API_URL%/}"
else
  PUBLIC_API_URL="$(
    PUBLIC_URL="$PUBLIC_URL" python3 <<'PY'
import os, urllib.parse, sys
ui = urllib.parse.urlparse(os.environ["PUBLIC_URL"])
if not ui.scheme or not ui.hostname:
    print("PUBLIC_URL must include scheme and host (e.g. https://app.example.com)", file=sys.stderr)
    sys.exit(2)
print(f"{ui.scheme}://{ui.hostname}:8000")
PY
  )"
fi

# Browser Origin must match exactly. If PUBLIC_URL has no port, users typically open Next on :3000
# (Compose default WEB_PORT); include that origin for CORS without requiring :3000 in PUBLIC_URL.
CORS_ORIGINS="$(
  PUBLIC_URL="$PUBLIC_URL" WEB_PORT="${WEB_PORT:-3000}" python3 <<'PY'
import os, urllib.parse, sys

ui = os.environ["PUBLIC_URL"].rstrip("/")
web_port = int(os.environ.get("WEB_PORT", "3000"))
p = urllib.parse.urlparse(ui)
if not p.scheme or not p.hostname:
    print("PUBLIC_URL must include scheme and host", file=sys.stderr)
    sys.exit(2)
origins = []
if p.port is not None:
    origins.append(ui)
else:
    origins.append(ui)
    if p.scheme == "http":
        with_port = f"{p.scheme}://{p.hostname}:{web_port}"
        if with_port.rstrip("/") != ui:
            origins.append(with_port)
print(",".join(dict.fromkeys(origins)))
PY
)"

export ALLOWED_ORIGINS="$CORS_ORIGINS"
export OBJECT_STORAGE_ALLOWED_ORIGINS="$CORS_ORIGINS"
export NEXT_PUBLIC_BASE_URL="$PUBLIC_API_URL"
export SERVER_API_BASE_URL="${SERVER_API_BASE_URL:-http://backend:8000}"

echo "Using:"
echo "  PUBLIC_URL=$PUBLIC_URL (UI; used for API host inference)"
echo "  ALLOWED_ORIGINS=$ALLOWED_ORIGINS"
echo "  OBJECT_STORAGE_ALLOWED_ORIGINS=$OBJECT_STORAGE_ALLOWED_ORIGINS"
echo "  NEXT_PUBLIC_BASE_URL=$NEXT_PUBLIC_BASE_URL (web image build arg)"
echo "  SERVER_API_BASE_URL=$SERVER_API_BASE_URL"
echo "Running: docker compose ${compose_args[*]}"
exec docker compose "${compose_args[@]}"
