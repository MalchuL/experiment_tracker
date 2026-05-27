# Docker small guide

## Docker: stop, remove containers, and reset for a new run

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

3. **Remove persisted data** (optional, destructive — empty databases and blobs next `up`):

   ```bash
   rm -rf storage/
   ```

4. **Remove built images** (optional — next `docker compose up --build` will rebuild):

   ```bash
   docker compose down --rmi local
   ```

   Or remove specific images with `docker image rm …` / `docker image prune`.

5. **Start again** from the [Full stack: step by step](#full-stack-step-by-step) section (e.g. `docker compose up -d --build` or `./scripts/docker-up-public.sh …`).

## Layout (no central `docker/` folder)

| Path | Role |
|------|------|
| `docker-compose.yml` | Full stack: two Postgres instances, Redis, ClickHouse, MinIO, object-storage, scalars, backend, web |
| `python/backend/Dockerfile` | Main API; `docker-entrypoint.sh` runs `uvicorn` (schema from SQLAlchemy models on startup) |
| `python/scalars_service/Dockerfile` | Scalars / ClickHouse API |
| `python/object_storage/Dockerfile` | Object storage API |
| `apps/web/Dockerfile` | Next.js standalone production image |

Python images declare `HEALTHCHECK` in their Dockerfiles so `depends_on: service_healthy` in Compose can gate startup. The runtime stage **recreates `.venv`** with `uv sync` on `python:3.13-slim-bookworm` so console scripts match that interpreter (the builder uses the `uv` image, which is a different layout than plain `python:slim`).

## Ports (defaults)

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

Host ports are overridden with variables in a root `.env` (see `.env.example`); the **container** port (right side of `host:container`) stays the same so services inside Compose keep talking to `redis:6379`, `postgres-backend:5432`, and so on.

## Port already in use on the host

If Compose fails with **`address already in use`** when binding a host port, something else on your machine already listens on that port.

1. Create or edit **`.env`** in the repository root (copy from `.env.example` if you do not have one yet).
2. Set a **free host port** for the service that failed. Examples:

   **Redis** (compose default host map **6380** so it does not fight a local `redis-server` on **6379**; set another value if **6380** is busy):

   ```env
   REDIS_PORT=6381
   ```

   **Postgres for object storage** (compose default host map **5434**; set another value if that port is busy):

   ```env
   POSTGRES_OBJECT_STORAGE_PORT=5436
   ```

   **Postgres for the main backend** (compose default host map **5435**; set another value if that port is busy):

   ```env
   POSTGRES_BACKEND_PORT=5436
   ```

3. Run `docker compose down` then `docker compose up -d` again (or add `--build` if you changed Dockerfiles).

Only the **published** host port (left side of `host:container` in `docker-compose.yml`) changes. Containers still talk to **`postgres-object-storage:5432`**, **`redis:6379`**, and so on inside the Compose network, so you do **not** need to change `DATABASE_URL` / `OBJECT_STORAGE_DATABASE_URL` / `REDIS_URL` for these host-port overrides.

Use the same idea for other clashes: `CLICKHOUSE_HTTP_PORT`, `BACKEND_PORT`, `WEB_PORT`, etc., as listed in `.env.example`.

## Known issues (Docker / MinIO)

- **MinIO fails to start: host port 9000 already in use.** The compose file publishes MinIO’s API on **`${MINIO_API_PORT:-9000}:9000`** (see `.env.example`). If something else on the host already listens on **9000**, set free ports in a root `.env`, then `docker compose down` and bring the stack up again:

  ```env
  MINIO_API_PORT=9010
  MINIO_CONSOLE_PORT=9011
  ```

  Services inside Compose still use **`minio:9000`**; only the **host** side of the map changes.

- **Older Docker Engine and `minio/minio:latest`.** On some older installations, the current **`minio/minio:latest`** image may not start or may exit immediately. Pin the server image to a known-good release, for example **`minio/minio:RELEASE.2024-11-07T00-52-20Z`**, by editing the `minio:` service `image:` line in `docker-compose.yml` (or using a Compose override file) instead of `:latest`.

- **After pinning MinIO or fixing bad local object storage state**, stop the stack, **clear persisted data** under **`storage/`** (destructive — empty blobs and any prior MinIO layout on disk), then start again:

  ```bash
  docker compose down
  rm -rf storage/*
  docker compose up -d --build
  ```

  If files were created as root, you may need `sudo rm -rf storage/*` once, then fix Docker permissions so future runs do not require root for that directory.

## CORS

Backend and object-storage read `ALLOWED_ORIGINS` / `OBJECT_STORAGE_ALLOWED_ORIGINS` from the environment. If you publish the UI on a different origin, set the matching comma-separated list in a root `.env` (see `.env.example`). For real hostnames, HTTPS, or splitting UI and API on different origins, use **Custom URL or domain** below (including rebuilding `web` when `NEXT_PUBLIC_BASE_URL` changes).


## Dependencies, startup order, and hybrid setups

Compose encodes dependencies with `depends_on` and `condition: service_healthy` (or `service_completed_successfully` for one-shot jobs). Docker starts **parents before children**; for example **`backend`** waits until **`postgres-backend`**, **`scalars`**, and **`object-storage`** are healthy, and those in turn wait on their own databases and MinIO where applicable.

### Case 1 — Everything in containers (recommended for a full stack)

Same flow as **Full stack: step by step** above (typically `docker compose up -d --build`). Inspect logs for one service with `docker compose logs -f backend`. The API is not expected to stay up if Postgres or the satellite services are down; fix the failing dependency first.

### Case 2 — Postgres (or other infra) in Docker, **backend on the host**

Use this when you want `uv run uvicorn …` against a database that still runs in Compose.

1. Start the containers you need and their transitive dependencies. The **`backend`** service in this file also depends on **`scalars`** and **`object-storage`**, which need ClickHouse, Redis, MinIO, and the second Postgres. A practical pattern is to start the **full dependency chain** but not the `web` image, for example:

   ```bash
   docker compose up -d postgres-backend postgres-object-storage redis clickhouse minio minio-init scalars object-storage
   ```

2. On the host, point URLs at **published ports** (see the ports table above). Defaults: backend DB `127.0.0.1:5435` (unless you set `POSTGRES_BACKEND_PORT`), object-storage DB `127.0.0.1:5434` (unless you set `POSTGRES_OBJECT_STORAGE_PORT`), scalars `127.0.0.1:8001`, object-storage API `127.0.0.1:8002`. Match users and databases to `docker-compose.yml` (defaults use user `tracker` and DB names `experiment_tracker` / `object_storage`).

   ```bash
   cd python/backend
   export DATABASE_URL="postgresql+asyncpg://tracker:tracker@127.0.0.1:5435/experiment_tracker"
   export SCALARS_SERVICE_URL="http://127.0.0.1:8001/api"
   export OBJECT_STORAGE_SERVICE_URL="http://127.0.0.1:8002/api"
   uv run uvicorn api.main:app --reload --port 8000
   ```

If you only start **`postgres-backend`** and run the backend on the host, you still need scalars and object-storage (or stub URLs) if your code paths call them; otherwise start the subset shown above.

### Case 3 — Postgres on the **host**, **`backend` in Docker**

The container must reach Postgres on the machine, not the hostname `postgres-backend` (that only resolves **inside** the Compose network).

1. Create the same database user and database on the host Postgres as your app expects (for example user `tracker`, database `experiment_tracker`).

2. In a root `.env` (or export before `compose`), set `DATABASE_URL` using a host alias Docker provides to the host gateway, for example:

   `DATABASE_URL=postgresql+asyncpg://tracker:tracker@host.docker.internal:5432/experiment_tracker`

3. On **Linux**, add a `docker-compose.override.yml` next to `docker-compose.yml` so the backend container can resolve `host.docker.internal` (Docker Desktop on Mac/Windows already provides it):

   ```yaml
   services:
     backend:
       extra_hosts:
         - "host.docker.internal:host-gateway"
   ```

4. Avoid port clashes: if your **host** Postgres already uses **5435**, set `POSTGRES_BACKEND_PORT` in `.env` to a different free host port so the two do not collide.

5. Start **`backend` without starting the compose Postgres service** (otherwise Compose would start `postgres-backend` for you). Use **`--no-deps`** so linked services are not started automatically:

   ```bash
   docker compose up -d --no-deps --build backend
   ```

   You still need **`scalars`** and **`object-storage`** (and their infra). Start them first, then bring up `backend`:

   ```bash
   docker compose up -d redis clickhouse minio minio-init postgres-object-storage scalars object-storage
   docker compose up -d --no-deps --build backend
   ```

   Inside the backend container, default `SCALARS_SERVICE_URL` / `OBJECT_STORAGE_SERVICE_URL` use Compose DNS names (`http://scalars:8001/api`, etc.), which work as long as those services run **in the same Compose project**. If you instead run scalars/object-storage with `docker run` on published host ports, set overrides in `.env`, for example `SCALARS_SERVICE_URL=http://host.docker.internal:8001/api` (and matching `extra_hosts` on Linux as in step 3).

### Shutting down and removing containers

From the repo root:

| Goal | Command |
|------|---------|
| Stop containers, keep them and images | `docker compose stop` |
| Stop and **remove** containers, default network; keep volumes (here: bind mounts under `./storage/`) | `docker compose down` |
| Same, plus remove anonymous volumes attached to containers | `docker compose down -v` |
| Remove stopped containers for this project | `docker compose rm` (often used after `stop`) |

**Data:** Postgres, Redis, ClickHouse, and MinIO data for this compose file live in **`./storage/`** on the host. `docker compose down` does **not** delete that folder. To wipe databases completely, stop the stack and remove the directories under `storage/` yourself (destructive).

**Images:** `docker compose down` does not remove built images. Remove them explicitly if needed, for example `docker image rm experiment-tracker-backend` (exact names depend on your image tags; `docker compose images` lists compose-built images).

## Build individual images

Each service `Dockerfile` uses **`COPY` paths from the repository root** (for example `COPY python/shared …`). **Always build with context `.`**, not from inside `python/backend` or `apps/web`.

From the repository root:

```bash
docker build -f python/backend/Dockerfile -t experiment-tracker-backend .
docker build -f python/scalars_service/Dockerfile -t experiment-tracker-scalars .
docker build -f python/object_storage/Dockerfile -t experiment-tracker-object-storage .
docker build -f apps/web/Dockerfile --build-arg NEXT_PUBLIC_BASE_URL=http://127.0.0.1:8000 -t experiment-tracker-web .
```

`NEXT_PUBLIC_BASE_URL` is inlined at **image build** time for the browser bundle; change it by rebuilding the web image or passing a different compose build arg.

Or build one service via Compose (same root context):

```bash
docker compose build backend
docker compose build scalars
docker compose build object-storage
docker compose build web
```

## Force rebuild (stale cache or odd build errors)

Docker reuses image layers when it thinks nothing changed. If a service still misbehaves after edits, rebuild **without cache** for that service, then start again.

**Compose — one service (from repo root):**

```bash
docker compose build --no-cache backend
docker compose build --no-cache web
docker compose up -d --force-recreate backend web
```

Use the real Compose service names: `object-storage`, `scalars`, `backend`, `web` (hyphen in `object-storage`).

**Compose — all app images that have a `build:` section:**

```bash
docker compose build --no-cache object-storage scalars backend web
docker compose up -d --force-recreate
```

`--force-recreate` replaces running containers so they pick up the new image. Omit `-d` if you prefer attached logs.

**Plain `docker build` (same context `.`, no Compose):**

```bash
docker build --no-cache -f python/backend/Dockerfile -t experiment-tracker-backend .
docker build --no-cache -f apps/web/Dockerfile --build-arg NEXT_PUBLIC_BASE_URL=http://127.0.0.1:8000 -t experiment-tracker-web .
```

If problems persist, clear build cache (affects all projects on the machine): `docker builder prune`, then rebuild with `--no-cache` again.
