# Runtime env and Docker (frontend)

## Why not `NEXT_PUBLIC_*` for API URLs

`NEXT_PUBLIC_*` is inlined into the client bundle at **build** time. Changing the backend URL would require rebuilding the image.

Prefer:

1. **`PUBLIC_API_BASE_URL`** — read by the Next.js **server process** when rendering. Injected into the HTML via `getRuntimeConfigScript()` before client JS runs.
2. **`SERVER_API_BASE_URL`** — server-only; used by Route Handlers that proxy to the API on the Docker network.

Same built image → different public API URLs by recreating the `web` container with new env (no rebuild).

## Local development

Document values in the frontend package `.env.example`:

```bash
PUBLIC_API_BASE_URL=http://127.0.0.1:8000
SERVER_API_BASE_URL=http://127.0.0.1:8000
# optional: NEXT_PUBLIC_API_PREFIX=/api
```

Run the frontend package with its usual package-manager scripts (`pnpm run dev`, Turbo from monorepo root, etc.).

## Docker image

For a pnpm monorepo, build context is usually the **repo root** (workspace manifests + frontend package):

```dockerfile
# Multi-stage Dockerfile in the frontend package
# builder: install deps + build the web package
# runner: copy .next/standalone + static + public; CMD node <standalone-server.js>
```

`next.config.ts` should set `output: "standalone"` and, in a monorepo, `outputFileTracingRoot` to the workspace root.

Example Compose `web` service:

```yaml
web:
  build:
    context: .
    dockerfile: apps/web/Dockerfile
  environment:
    NODE_ENV: production
    PORT: "3000"
    HOSTNAME: "0.0.0.0"
    # Browser-reachable API origin (injected at container runtime)
    PUBLIC_API_BASE_URL: ${PUBLIC_API_BASE_URL:-http://127.0.0.1:8000}
    # Server-side BFF → API on the Compose network
    SERVER_API_BASE_URL: ${SERVER_API_BASE_URL:-http://backend:8000}
  ports:
    - "${WEB_PORT:-3000}:3000"
```

| Env | Typical Compose value | Who uses it |
|-----|----------------------|-------------|
| `PUBLIC_API_BASE_URL` | Host-reachable or public HTTPS API origin | Browser axios (`getPublicApiBaseUrl`) |
| `SERVER_API_BASE_URL` | `http://backend:8000` (Compose DNS) | Next Route Handlers (`getServerApiBaseUrl`) |

When using a custom hostname, set backend CORS allowlists to the **UI** origin. After changing only `PUBLIC_API_BASE_URL`:

```bash
docker compose up -d --force-recreate web
```

No image rebuild required.

## Code touchpoints

| File | Role |
|------|------|
| `src/lib/runtime-config.ts` | Public URL resolve + HTML injection script |
| `src/lib/env.ts` | Zod env; `getServerApiBaseUrl()` |
| `src/app/layout.tsx` | Injects config script; `force-dynamic` |
| `src/lib/api/clients/axios-client.ts` | Browser client `baseURL` |
| `src/app/api/**/route.ts` | Server proxy with `getServerApiBaseUrl()` |

Never put secrets or internal-only URLs into the runtime config object injected for the browser.
