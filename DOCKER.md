# Docker Guide

## Docker (full stack)

There are two root Compose files:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Deployment-style stack. Pulls application images from GHCR and publishes only the UI (`3000`) and backend (`8000`) to the host. |
| `docker-compose.dev.yml` | Local Docker development stack. Builds application images from this checkout and publishes dependency/service ports for hybrid development. |

## Full stack: step by step

1. **Work from the repository root** (the folder that contains `docker-compose.yml`).

2. **Optional environment file.** Copy `.env.example` to `.env` to override secrets, CORS, public ports, `GHCR_NAMESPACE`, or `IMAGE_TAG`. Application images resolve as `ghcr.io/${GHCR_NAMESPACE}/experiment-tracker-<service>:${IMAGE_TAG}`. Defaults are `GHCR_NAMESPACE=malchul` and `IMAGE_TAG=0.12.1`.

3. **`storage/` on disk.** Data is persisted under **`./storage/`** (for example `storage/postgres-backend`, `storage/clickhouse`). **You do not need to create these directories yourself:** Docker creates missing host paths for bind mounts when the containers start.

4. **Pull GHCR images and start the deployment stack**:

   ```bash
   docker compose pull
   docker compose up -d
   ```

   If the GHCR packages are private, run `docker login ghcr.io` first.

   To build from the current checkout instead:

   ```bash
   docker compose -f docker-compose.dev.yml up -d --build
   ```

5. **Wait for health checks.** `web` starts only after `backend` is healthy; `backend` waits on Postgres, scalars, and object-storage. Watch status and logs:

   ```bash
   docker compose ps
   docker compose logs -f backend
   ```

   Press Ctrl+C to stop tailing logs; containers keep running.

6. **Open the UI.** With default host ports, the Next.js app is:

   **http://localhost:3000** (equivalently **http://127.0.0.1:3000**)

   The main API is on **http://localhost:8000**. The web container injects `PUBLIC_API_BASE_URL` into the frontend at runtime, so the same GHCR image can be used with different public API URLs.

**That's it!** You can now start training your models and track your experiments.
---

## Publish application images to GHCR

The **Build and publish Docker images** GitHub Actions workflow runs only when manually started. Pushes, pull requests, and merges do not trigger it.

1. Open **Actions** → **Build and publish Docker images** → **Run workflow**.
2. Select the branch to build.
3. Enter the additional image tag to publish, normally `latest` or a release such as `v1.2.0`.
4. Run the workflow.

It publishes `backend`, `scalars`, `object-storage`, and `web` images under `ghcr.io/<repository-owner>/experiment-tracker-*`. Every image receives the selected tag and the full commit SHA. Use the SHA tag in `IMAGE_TAG` for an immutable deployment.

## Custom URL or domain (not `localhost` / `127.0.0.1`)

Use this when the UI or API is reached under a **real hostname**, **HTTPS**, or a **non-default port** on another machine (for example `https://tracker.example.com` for the app and `https://api.example.com` for the API).


### One command without a `.env` file (`PUBLIC_URL`)

From the repository root you can export everything from a **single UI origin** and start the stack (no root `.env` required). Simplest forms:

```bash
PUBLIC_URL=http://192.168.1.242 ./scripts/docker-up-public.sh
```

`docker-up-public.sh` starts the deployment stack from **`docker-compose.yml`**. To build application images from the current checkout with **`docker-compose.dev.yml`**, use the same arguments with **`docker-up-dev.sh`**:

```bash
PUBLIC_URL=http://192.168.1.242 ./scripts/docker-up-dev.sh
```

If the UI is on a **non-default** published port, set **`WEB_PORT`** (defaults to **3000**). For `http://…` URLs **without** an explicit port, the script adds **`http://<host>:<WEB_PORT>`** to **`ALLOWED_ORIGINS`** as well as the bare URL, so the browser `Origin` from `http://192.168.1.247:3000` matches after `PUBLIC_URL=http://192.168.1.247`. You can still set **`PUBLIC_URL=http://192.168.1.247:3000`** explicitly if you prefer a single origin string.

```bash
./scripts/docker-up-public.sh https://dashboard.example.com
```

Both scripts set **`ALLOWED_ORIGINS`**, **`OBJECT_STORAGE_ALLOWED_ORIGINS`**, and runtime **`PUBLIC_API_BASE_URL`**, and keep **`SERVER_API_BASE_URL=http://backend:8000`**. `docker-up-public.sh` starts **`docker-compose.yml`**; `docker-up-dev.sh` builds and starts **`docker-compose.dev.yml`**.

- **Different API host:** pass a second URL:
  `./scripts/docker-up-public.sh https://dashboard.example.com https://api.example.com`
- **Same as env var:**
  `PUBLIC_URL=https://dashboard.example.com ./scripts/docker-up-public.sh`
- **Only `PUBLIC_URL`:** the script is the supported “single variable” entrypoint; it fills in the other exports for Compose.
- **Different compose invocation:** append `--` and arguments, e.g.
  `./scripts/docker-up-public.sh http://myhost:3000 -- up -d`

Override the in-container BFF target only if needed:
`SERVER_API_BASE_URL=http://other:8000 PUBLIC_URL=... ./scripts/docker-up-public.sh`

### If docker compose only works with sudo

- **`docker compose …`** and **`./scripts/docker-up-public.sh`** (it ends with `docker compose …`): normally **no `sudo`** if your user can talk to the Docker daemon (Linux: user is in the **`docker`** group, or Docker Desktop on Mac/Windows). If you see *permission denied* on the Docker socket, you can run Compose **with** `sudo` until permissions are fixed (not ideal long-term).
- **`sudo` and `PUBLIC_URL` for `docker-up-public.sh`:** assignments **between** `sudo` and the program are passed into **that** command’s environment (not the same as `PUBLIC_URL=…` *before* `sudo`, which applies only to your shell, not to root’s process). Typical pattern:

  ```bash
  sudo PUBLIC_URL=http://192.168.1.247 ./scripts/docker-up-public.sh
  sudo PUBLIC_URL=http://192.168.1.247 WEB_PORT=3000 ./scripts/docker-up-public.sh
  ```

  **Alternative:** pass URLs as arguments so nothing depends on env (works even when assignment-style `sudo` is restricted by `sudoers`):

  ```bash
  sudo ./scripts/docker-up-public.sh http://192.168.1.247
  sudo ./scripts/docker-up-public.sh http://192.168.1.247 http://192.168.1.247:8000
  ```

  If you already **exported** `PUBLIC_URL` / `WEB_PORT` in your shell and need root to see them, use **`sudo -E`** (preserve environment) or inline vars: **`sudo -E env PUBLIC_URL=… WEB_PORT=… ./scripts/docker-up-public.sh`**. **`-E` is a `sudo` flag**, not a `bash` flag. If the script is not executable, use `sudo PUBLIC_URL=… bash ./scripts/docker-up-public.sh`.

  Running the script as root can create **root-owned files** under `./storage/`; prefer adding your user to the **`docker`** group and running **without** `sudo`.

- **`rm -rf storage/`**: usually **no `sudo`** if files are owned by your user. If containers ran as root and created root-owned files under `./storage`, removal may fail until you run **`sudo rm -rf storage/`** once (then prefer running Docker with a user mapping or fix ownership with `sudo chown -R "$USER:$USER" storage/` if you want to avoid root-owned bind mounts).
- **Installing Docker or changing groups** is a one-time admin task and may require `sudo` or an administrator account on your OS.

### If you want to run docker compose with custom URL

1. **Configure root `.env`** next to `docker-compose.yml`. Set at least:

   | Variable | Who consumes it | What to set |
   |----------|-----------------|-------------|
   | `PUBLIC_API_BASE_URL` | **Web** container at **runtime** | Full base URL of the **main API as the user’s browser calls it**. The Next.js server injects it into the frontend. |
   | `ALLOWED_ORIGINS` | **Backend** container | Comma-separated **origins of the UI** exactly as the browser sends them in `Origin` (scheme + host + port). Example: `https://tracker.example.com`. Add `http://localhost:3000` too if you still use local dev against the same backend. |
   | `OBJECT_STORAGE_ALLOWED_ORIGINS` | **object-storage** container | Same idea as `ALLOWED_ORIGINS` (browser talks to object-storage for some flows). Usually match `ALLOWED_ORIGINS`. |
   | `SERVER_API_BASE_URL` | **Web** container at **runtime** | Leave the default **`http://backend:8000`** when `web` and `backend` are both services in this Compose file. Only override if your Next server reaches the API by a different internal URL. |

   `PUBLIC_API_BASE_URL` is intentionally browser-visible. `SERVER_API_BASE_URL`
   is used only by the remaining Next.js artifact proxy routes and can use private
   Compose DNS.

2. **Recreate `web`** after changing `PUBLIC_API_BASE_URL`; no image rebuild is required:

   ```bash
   docker compose up -d --force-recreate web
   ```

3. **Restart backend and object-storage** after changing CORS variables (no rebuild required unless you changed code):

   ```bash
   docker compose up -d --force-recreate backend object-storage
   ```

4. **Reverse proxy / TLS** in front of Compose: the browser must still be able to resolve `PUBLIC_API_BASE_URL` to your API and the UI origin must appear in `ALLOWED_ORIGINS`. Service-to-service URLs inside Compose (`http://backend:8000`, `http://scalars:8001/api`, etc.) stay on the Docker network and do not need to use your public domain.

## Detailed Reference and Known Issues

### Docker: stop, remove containers, and reset for a new run

Typical order when you want the stack **gone** and then a **clean start** next time:

1. **Stop containers** (keeps containers and volumes; fastest pause):

   ```bash
   docker compose stop
   ```

2. **Stop and remove containers and the Compose project network** (usual teardown; **data under `./storage/` stays** unless you delete it separately):

   ```bash
   docker compose down
   ```

   Add **`--remove-orphans`** if you changed service names and old containers remain. Add **`-v`** only if you use **named Docker volumes** in this project and want them removed too (this compose file mainly uses **bind mounts** to `./storage`, so `-v` often does nothing for data persistence).

3. **Remove persisted data** (optional, destructive; empty databases and blobs next `up`):

   ```bash
   rm -rf storage/
   ```

4. **Remove built images** (optional; next `docker compose up --build` will rebuild):

   ```bash
   docker compose down --rmi local
   ```

5. **Start again** from [Full stack: step by step](#full-stack-step-by-step).

### Layout

| Path | Role |
|------|------|
| `docker-compose.yml` | Deployment stack using published application images |
| `docker-compose.dev.yml` | Development stack building application images from this checkout |
| `python/backend/Dockerfile` | Main API |
| `python/scalars_service/Dockerfile` | Scalars and ClickHouse API |
| `python/object_storage/Dockerfile` | Object storage API |
| `apps/web/Dockerfile` | Next.js standalone production image |

Python images declare `HEALTHCHECK` in their Dockerfiles so `depends_on: service_healthy` can gate startup.

### Development stack ports

The deployment stack publishes only web and backend ports. The development stack also publishes dependency and satellite-service ports:

| Host port | Service |
|-----------|---------|
| 3000 | web |
| 8000 | backend |
| 8001 | scalars |
| 8002 | object-storage |
| 5435 | postgres (backend DB) |
| 5434 | postgres (object storage DB) |
| 6380 | redis |
| 8123 | ClickHouse HTTP |
| 9000 / 9001 | MinIO API / console |

Host ports are overridden with variables in a root `.env` (see `.env.example`). Container ports stay the same so services inside Compose keep talking to names such as `redis:6379` and `postgres-backend:5432`.

### Port already in use on the host

If Compose fails with **`address already in use`**, create or edit root `.env` and set a free host port for the failing service:

```env
REDIS_PORT=6381
POSTGRES_OBJECT_STORAGE_PORT=5436
POSTGRES_BACKEND_PORT=5437
MINIO_API_PORT=9010
MINIO_CONSOLE_PORT=9011
```

Then restart:

```bash
docker compose down
docker compose up -d
```

Only the published host port changes. Containers continue using their unchanged internal service names and ports.

### Known issues (Docker / MinIO)

- **MinIO fails to start because host port 9000 is already in use.** Set `MINIO_API_PORT` and `MINIO_CONSOLE_PORT` to free ports in root `.env`, then restart the stack.
- **Older Docker Engine and `minio/minio:latest`.** On some older installations, the current image may exit immediately. Pin the `minio` service to a known-good release such as `minio/minio:RELEASE.2024-11-07T00-52-20Z`.
- **Bad or incompatible local object-storage state.** Stop the stack, clear persisted data, then start again. This is destructive:

  ```bash
  docker compose down
  rm -rf storage/*
  docker compose up -d
  ```

  If files were created as root, you may need `sudo rm -rf storage/*` once, then fix Docker permissions.

### Dependencies, startup order, and hybrid setups

Compose uses `depends_on` with health conditions. For example, backend waits for PostgreSQL, scalars, and object-storage, which wait on their own dependencies.

For a complete containerized stack:

```bash
docker compose up -d
docker compose logs -f backend
```

To run backend on the host while dependencies run in the development stack:

```bash
docker compose -f docker-compose.dev.yml up -d postgres-backend postgres-object-storage redis clickhouse minio minio-init scalars object-storage
cd python/backend
export DATABASE_URL="postgresql+asyncpg://tracker:tracker@127.0.0.1:5435/experiment_tracker"
export SCALARS_SERVICE_URL="http://127.0.0.1:8001/api"
export OBJECT_STORAGE_SERVICE_URL="http://127.0.0.1:8002/api"
uv run uvicorn api.main:app --reload --port 8000
```

To run backend in Docker while PostgreSQL runs on the host, set `DATABASE_URL` to use `host.docker.internal`. On Linux, add this Compose override:

```yaml
services:
  backend:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Then start backend without its Compose PostgreSQL dependency:

```bash
docker compose up -d --no-deps backend
```

## Local Development

To run the development stack locally, you can use the following commands:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

This will start the development stack with the dependencies running on the host.

### Build individual images

Each Dockerfile uses paths from the repository root. Always build with context `.`:

```bash
docker build -f python/backend/Dockerfile -t experiment-tracker-backend .
docker build -f python/scalars_service/Dockerfile -t experiment-tracker-scalars .
docker build -f python/object_storage/Dockerfile -t experiment-tracker-object-storage .
docker build -f apps/web/Dockerfile -t experiment-tracker-web .
```

Or build individual development-stack services:

```bash
docker compose -f docker-compose.dev.yml build backend
docker compose -f docker-compose.dev.yml build scalars
docker compose -f docker-compose.dev.yml build object-storage
docker compose -f docker-compose.dev.yml build web
```

### Force rebuild

If a service still misbehaves after edits, rebuild without cache and recreate it:

```bash
docker compose -f docker-compose.dev.yml build --no-cache backend web
docker compose -f docker-compose.dev.yml up -d --force-recreate backend web
```

For all application services:

```bash
docker compose -f docker-compose.dev.yml build --no-cache object-storage scalars backend web
docker compose -f docker-compose.dev.yml up -d --force-recreate
```

If problems persist, `docker builder prune` clears build cache for all Docker projects on the machine.
