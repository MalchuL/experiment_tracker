# Experiment Tracker: Research-First Machine Learning Experiment Tracking

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-UI-000000?logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-relational%20state-4169E1?logo=postgresql&logoColor=white)
![ClickHouse](https://img.shields.io/badge/ClickHouse-scalars-FFCC01?logo=clickhouse&logoColor=black)
![MinIO](https://img.shields.io/badge/MinIO-object%20storage-C72E49?logo=minio&logoColor=white)
![S3 Compatible](https://img.shields.io/badge/S3-compatible%20blobs-569A31?logo=amazons3&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-self--hosted-2496ED?logo=docker&logoColor=white)
![SDK](https://img.shields.io/badge/Python%20SDK-training%20logs-4B8BBE?logo=python&logoColor=white)

Experiment Tracker is an open-source, self-hosted machine learning experiment tracker for researchers who need a clear view of training runs, model metrics, scalar curves, logged artifacts, and experiment lineage. It is built for research analysis: compare models, summarize results, inspect training behavior, and keep the broader picture of many experiments visible in one workspace.

The project focuses on experiment understanding instead of remote execution or production serving. Use it when your team needs better research notes, model comparison, scalar visualization, artifact review, and reproducible experiment history.

## Why Experiment Tracker Can Help in Your Research

- **Compare machine learning experiments:** review accuracy, loss, precision, recall, mAP, custom scores, and final metric snapshots across many runs.
- **Analyze scalar curves:** inspect training and validation metrics over time with multi-run charts, smoothing, synced axes, and saved visual views.
- **Review model artifacts:** view logged images, predictions, generated samples, checkpoints, configs, and project-level files alongside experiment context.
- **Track experiment lineage:** connect parent and child runs to understand how model variants, hyperparameter changes, and research branches evolved.
- **Summarize research results:** keep metrics, scalars, artifacts, reports, hypotheses, and project notes together so researchers can see the wide picture of model training.
- **Run locally or self-host:** use the Python SDK, FastAPI services, Next.js UI, PostgreSQL, ClickHouse, and S3-compatible object storage in a Docker-based stack.

## Machine Learning Experiment Comparison

<img src="mics/metrics_page_example.png" alt="Machine learning experiment tracker metrics table for comparing model accuracy loss precision recall and mAP" width="100%">

### Features for researchers

- **Metrics-first model comparison:** compare final or labeled metric snapshots across experiments in a dense grid, filter runs, export tables, and inspect selected experiment metadata in the side panel.
- **Research result summaries:** organize project metrics, experiment status, tags, notes, and SDK-driven training logs in one place for faster model selection.

## Scalar Metrics and Logged Artifacts

<img src="mics/scalars_view_example.png" alt="Machine learning scalar metrics dashboard with training curves validation loss and logged prediction image artifacts" width="100%">

### Features for researchers

- **Interactive scalar analysis:** visualize multi-run scalar curves with synchronized axes, smoothing, resizable cards, saved views, and selective visibility for each metric stream.
- **Artifact review beside metrics:** inspect image and object artifacts next to scalar trends, grouped by type and name, with step-aware controls for model outputs such as predictions or generated samples.

## Experiment Lineage and Research History

<img src="mics/dag_view_example.png" alt="Experiment lineage graph for machine learning research showing parent child runs and metric deltas" width="100%">

### Features for researchers

- **Experiment lineage graph:** track parent-child relationships between runs, compare metric deltas along branches, and understand how research iterations evolved.
- **Iteration analysis:** follow branches from baseline to follow-up runs, compare metric movement at each node, and preserve the context behind research decisions.

## Core Capabilities

| Area | What it helps researchers do |
|------|-------------------------------|
| Experiment tracking | Record runs, status, tags, metadata, notes, and project context. |
| Metrics comparison | Compare final scores and labeled metric snapshots across models. |
| Scalar visualization | Explore training curves for loss, accuracy, learning rate, validation metrics, and custom scalars. |
| Artifact logging | Store and review experiment artifacts and project-level files. |
| Research organization | Keep hypotheses, reports, kanban items, and lineage connected to experiments. |
| Self-hosted stack | Run the UI, API, scalars service, and object storage with Docker or local development tools. |

## Local Development

For manual local setup with Postgres, MinIO, ClickHouse, the Python services, and the Next.js frontend, see [LOCAL_RUN.md](LOCAL_RUN.md).

## Docker (full stack)

Run **all** services from `docker-compose.yml` (Postgres ×2, Redis, ClickHouse, MinIO, object-storage, scalars, backend, web). Hybrid setups, dependency details, and aggressive cache busting are covered in the sections below.

## Full stack: step by step

1. **Work from the repository root** (the folder that contains `docker-compose.yml`).

2. **Optional environment file.** To override ports, `JWT_SECRET`, `NEXT_PUBLIC_BASE_URL`, CORS, and so on, copy `.env.example` to `.env` in that same folder. If you skip this, Compose uses the defaults in `docker-compose.yml`. For a **single public UI URL** without maintaining `.env`, use **`./scripts/docker-up-public.sh`** (see **Custom URL or domain** → *One command without a `.env` file*). For local `uv` / `pnpm` development (without Docker), see each package `python/backend/.env.example`, `python/scalars_service/.env.example`, `python/object_storage/.env.example`, and `apps/web/.env.example`.

3. **`storage/` on disk.** Data is persisted under **`./storage/`** (for example `storage/postgres-backend`, `storage/clickhouse`). **You do not need to create these directories yourself:** Docker creates missing host paths for bind mounts when the containers start.

4. **Build images and start the stack** (detached):

   ```bash
   docker compose up -d --build
   ```

   Use `docker compose -f docker-compose.yml …` if you need an explicit file path. The first run can take several minutes. Omit `--build` when you only changed runtime env and the images are already built.

5. **Wait for health checks.** `web` starts only after `backend` is healthy; `backend` waits on Postgres, scalars, and object-storage. Watch status and logs:

   ```bash
   docker compose ps
   docker compose logs -f backend
   ```

   Press Ctrl+C to stop tailing logs; containers keep running.

6. **Open the UI.** With default host ports, the Next.js app is:

   **http://localhost:3000** (equivalently **http://127.0.0.1:3000**)

   The main API is on **http://localhost:8000** (interactive docs are usually at **http://localhost:3000/docs** for the UI and **http://localhost:8000/docs** for the swagger UI). The web image is built with `NEXT_PUBLIC_BASE_URL` (compose default **http://127.0.0.1:8000**) so the **browser** loads the API from your machine; if you change host ports, use a **custom domain**, or publish the UI elsewhere, set the variables in **Custom URL or domain** below and **rebuild** `web` (see `.env.example`).

**That's it!** You can now start training your models and track your experiments.
---

## Custom URL or domain (not `localhost` / `127.0.0.1`)

Use this when the UI or API is reached under a **real hostname**, **HTTPS**, or a **non-default port** on another machine (for example `https://tracker.example.com` for the app and `https://api.example.com` for the API).


### One command without a `.env` file (`PUBLIC_URL`)

From the repository root you can export everything from a **single UI origin** and start the stack (no root `.env` required). Simplest forms:

```bash
PUBLIC_URL=http://192.168.1.242 ./scripts/docker-up-public.sh
```

If the UI is on a **non-default** published port, set **`WEB_PORT`** (defaults to **3000**). For `http://…` URLs **without** an explicit port, the script adds **`http://<host>:<WEB_PORT>`** to **`ALLOWED_ORIGINS`** as well as the bare URL, so the browser `Origin` from `http://192.168.1.247:3000` matches after `PUBLIC_URL=http://192.168.1.247`. You can still set **`PUBLIC_URL=http://192.168.1.247:3000`** explicitly if you prefer a single origin string.

```bash
./scripts/docker-up-public.sh https://dashboard.example.com
```

The script sets **`ALLOWED_ORIGINS`** and **`OBJECT_STORAGE_ALLOWED_ORIGINS`** (see above for the `http` + no-port case), sets **`NEXT_PUBLIC_BASE_URL`** to the same host with port **8000** unless you pass a second URL (so `http://192.168.1.242` implies `http://192.168.1.242:8000` for the API), keeps **`SERVER_API_BASE_URL=http://backend:8000`**, then runs **`docker compose up -d --build`**.

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

**Root `.env`** (repository root, next to `docker-compose.yml`). Set at least:

   | Variable | Who consumes it | What to set |
   |----------|-----------------|-------------|
   | `NEXT_PUBLIC_BASE_URL` | **Web image build** (`web` Dockerfile build-arg) | Full base URL of the **main API as the user’s browser calls it** (scheme + host + port if not 443/80). Example: `https://api.example.com`. No trailing slash. This value is baked into the Next.js client bundle. |
   | `ALLOWED_ORIGINS` | **Backend** container | Comma-separated **origins of the UI** exactly as the browser sends them in `Origin` (scheme + host + port). Example: `https://tracker.example.com`. Add `http://localhost:3000` too if you still use local dev against the same backend. |
   | `OBJECT_STORAGE_ALLOWED_ORIGINS` | **object-storage** container | Same idea as `ALLOWED_ORIGINS` (browser talks to object-storage for some flows). Usually match `ALLOWED_ORIGINS`. |
   | `SERVER_API_BASE_URL` | **Web** container at **runtime** | Leave the default **`http://backend:8000`** when `web` and `backend` are both services in this Compose file. Only override if your Next server reaches the API by a different internal URL. |

2. **Rebuild the `web` image** after changing `NEXT_PUBLIC_BASE_URL` (it is read at `next build`, not at container start):

   ```bash
   docker compose build web --no-cache
   docker compose up -d web
   ```

3. **Restart backend and object-storage** after changing CORS variables (no rebuild required unless you changed code):

   ```bash
   docker compose up -d --force-recreate backend object-storage
   ```

4. **Reverse proxy / TLS** in front of Compose: the browser must still be able to resolve `NEXT_PUBLIC_BASE_URL` to your API and the UI origin must appear in `ALLOWED_ORIGINS`. Service-to-service URLs inside Compose (`http://backend:8000`, `http://scalars:8001/api`, etc.) stay on the Docker network and do not need to use your public domain.

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
