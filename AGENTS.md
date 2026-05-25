# AGENTS

Guidance for coding agents working on this repository: architecture, layout, and how to run things.

## High-level architecture

This is a **monorepo** for an **ML experiment tracker**: projects, experiments, metrics/scalars, and file artifacts (per experiment or per project). The browser talks to a **Next.js** app, which proxies API calls to a **Python backend**. The backend owns **relational state** (PostgreSQL) and orchestrates two satellite services: **scalars** (time-series and artifact metadata in ClickHouse) and **object storage** (content-addressed blobs in S3-compatible storage).

```mermaid
flowchart LR
  Web["apps/web\n(Next.js)"]
  API["python/backend\n(FastAPI + Postgres)"]
  Scalars["python/scalars_service\n(FastAPI + ClickHouse)"]
  Blobs["python/object_storage\n(FastAPI + MinIO/S3)"]
  SDK["python/sdk\n(client library)"]

  Web -->|"HTTP / BFF routes"| API
  API --> Scalars
  API --> Blobs
  SDK --> API
```

- **Frontend (`apps/web`)**: UI, dashboard, charts. Uses **Route Handlers** under `src/app/api/` as a BFF that forwards to the backend with auth cookies/headers.
- **Backend (`python/backend`)**: Primary API (`api.main:app`), users/teams/RBAC, projects, experiments, hypotheses, metrics orchestration. Calls **scalars_service** and **object_storage** via HTTP clients in `src/clients/`.
- **Scalars service (`python/scalars_service`)**: Stores scalar runs, tags, **artifacts_info** tables (per-project), and related query APIs. Backed by **ClickHouse** (and supporting infra as configured in that package).
- **Object storage (`python/object_storage`)**: Upload/download/delete for experiment and project blobs; uses **MinIO** or **S3** and metadata in Postgres.
- **SDK (`python/sdk`)**: `experiment_tracker_sdk` — typed HTTP client used by training jobs and tools to talk to the backend API.
- **Shared (`python/shared`)**: Shared Python types/utilities consumed by other Python packages where applicable.

## Repository layout (where things live)

| Path | Role |
|------|------|
| Repo root (`package.json`, `pnpm-workspace.yaml`, `turbo.json`) | pnpm workspace + Turborepo only (no application source here). |
| `apps/web/` | Next.js app (pnpm). UI, `src/app/api/*` BFF proxies to backend. Shared frontend-only types such as API `User` live under `apps/web/src/types/`. |
| `python/backend/src/` | FastAPI app: `api/` routes, `domain/*` bounded contexts, `clients/*` HTTP clients, `db/`, `lib/`. |
| `python/scalars_service/src/` | FastAPI scalars/artifacts_info service. `GET /scalars/get/...` paginates **experiments** first, then loads each metric column with ClickHouse `IS NOT NULL` + per-(experiment, column) uniform `max_points` sampling (`columns_per_query` controls parallel column queries; default 1). Cross-table ClickHouse work (delete experiment rows across scalars + artifacts_info + last_logged, usage, admin table listing) is under **`/projects`** (`projects` domain); compaction stays **`POST /scalars/projects/{id}/compact-columns`**. |
| `python/object_storage/src/` | FastAPI storage service (buckets, experiment/project artifacts). |
| `python/sdk/src/experiment_tracker_sdk/` | Public Python SDK for the tracker API. |
| `python/sdk/src/experiment_tracker_sdk/api_access.py` | Singleton :class:`ExpTrackerApiAccess` — shared ``APIRequestsRegistry`` / :class:`ExperimentTrackerClient` construction (used by :class:`ExpTracker` and CLI). |
| `python/sdk/src/experiment_tracker_sdk/constants.py` | Default API base URL and ``/api`` prefix literals shared with settings. |
| `python/sdk/src/experiment_tracker_sdk/settings.py` | Pydantic ``BaseSettings`` with ``EXP_TRACKER_`` env prefix and optional ``.env`` (CLI init defaults). |
| `python/sdk/src/experiment_tracker_sdk/console/` | CLI (`experiment-tracker`): **Click** group + `run` command; argv split on `--` via a small `click.Command` subclass; pluggable bootstrap hooks; in-process `runpy` (simple experiments only). |
| `python/shared/` | Shared package (`experiment-tracker-shared`). |
| `examples/training/` | Example training integration (optional). |
| `turbo.json` | Turborepo task graph (`build`, `dev`, etc.). |

Domain concepts in the backend are grouped under `python/backend/src/domain/` (e.g. `experiments/`, `projects/`, `metrics/`, `scalars/`, `experiment_artifacts/`, `project_artifacts/`, `rbac/`, `team/`, `api_tokens/`).

## Artifact logging flows

Training code and UIs upload files through three different patterns. **SDK URL templates** live in request-spec factories; **HTTP clients** in the backend point at the satellite services.

| Layer | Experiment @ step | Experiment named (no step) | Project CAS (shared) |
|-------|---------------------|------------------------------|------------------------|
| **SDK endpoint definitions** | `python/sdk/src/experiment_tracker_sdk/client/domain/experiment_artifacts/service.py` (`ENDPOINTS`, e.g. `log-at-step`) | Same package: `upsert` / `get` / `download` routes | `python/sdk/src/experiment_tracker_sdk/client/domain/project_artifacts/service.py` (`BASE_ENDPOINT = /api/project-artifacts`) |
| **SDK convenience API** | `python/sdk/src/experiment_tracker_sdk/client/blob_api.py` (`upload_and_log_experiment_artifact_at_step`) | `blob_api.py` (`upsert_named_experiment_artifact`, etc.) | `blob_api.py` (`upload_project_artifact`: hash check + upload) |
| **High-level trainer** | `python/sdk/src/experiment_tracker_sdk/exp_tracker.py` (`_upload_and_log_experiment_artifact_at_step`, `_upload_project_artifact`) | (named flows often via direct API / blob helpers) | `_upload_project_artifact` |
| **API composition** | `python/sdk/src/experiment_tracker_sdk/client/api.py` exposes `experiment_artifacts` and `project_artifacts` factories | | |

### 1) Upload **at step** (logged objects during training)

Use case: images, audio, or other outputs tied to **`global_step`**, with metadata in scalars for UI queries (by step, name, type).

1. **SDK** builds `POST /api/experiment-artifacts/{experiment_id}/log-at-step` (multipart: file + `name`, `artifact_type`, `step`, optional `metadata` / `tags`). See `experiment_artifacts/service.py` and `blob_api.upload_and_log_experiment_artifact_at_step`.
2. **Backend** `python/backend/src/domain/experiment_artifacts/controller.py` → `ExperimentArtifactsService.upload_and_log_experiment_artifact_at_step` in `domain/experiment_artifacts/service.py`.
3. **Object storage**: upload **untracked** blob; service computes/stores content and returns a **content hash** used as the logical key. The backend calls through `python/backend/src/clients/object_storage/client.py` → object_storage routes such as `POST .../experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-untracked` (see `python/object_storage/src/object_storage/domain/experiment_artifacts_storage/controller.py`).
4. **Scalars**: backend calls `python/backend/src/clients/artifacts_info/client.py` → `POST /artifacts_info/log/{project_id}/{experiment_id}` on **scalars_service**, which persists a row in **artifacts_info** (step, name, type, **path = hash**, metadata). Implementation: `python/scalars_service/src/app/domain/artifacts_info/` (`controller.py`, `service.py`).

Downloads at step resolve **hash via scalars** (`get_artifacts` with step/name filters) then fetch bytes from object storage — see `download_experiment_artifact_at_step` in the same backend service.

```mermaid
sequenceDiagram
  participant SDK
  participant Backend
  participant Obj as object_storage
  participant Sc as scalars_service

  SDK->>Backend: POST log-at-step (multipart)
  Backend->>Obj: upload untracked blob → hash
  Backend->>Sc: POST artifacts_info log (hash, step, name, type, …)
```

### 2) Upload **without step** (named / “tracked” experiment artifacts)

Use case: checkpoints, configs, final exports: stable **`name` + `filepath`**, rich metadata and listing — **no** `artifacts_info` / step table in scalars.

1. **SDK** uses routes like **`POST /api/experiment-artifacts/upsert`** (see `experiment_artifacts/service.py` and `blob_api.upsert_named_experiment_artifact`).
2. **Backend** `python/backend/src/domain/experiment_artifacts/controller.py` (`/upsert`) → `ExperimentArtifactsService.upsert_experiment_artifact` in `service.py`.
3. **Object storage** only: **tracked** upload with `file_path`, content hash, MIME type, and metadata; the **object_storage** service stores the blob and **database rows** for listing (hash, path, filename-derived fields, etc.). Client paths are defined in `python/backend/src/clients/object_storage/client.py` (e.g. `upload-tracked`, list/delete artifact routes under `experiment-artifacts/projects/.../experiments/...`).

This path does **not** call **scalars_service** `artifacts_info` for logging.

### 3) Upload to **project** scope (shared across experiments)

Use case: **code snapshots, datasets, shared assets** — **content-addressed storage (CAS)** per project so identical bytes are stored once and referenced by hash.

1. **SDK** (`blob_api.upload_project_artifact`): compute SHA-256 → **`POST /api/project-artifacts/{project_id}/check`** with hashes → if hash **missing**, **`POST /api/project-artifacts/{project_id}/upload?hash=...`** with file. Endpoints: `python/sdk/src/experiment_tracker_sdk/client/domain/project_artifacts/service.py`.
2. **Backend** `python/backend/src/domain/project_artifacts/controller.py` + `domain/project_artifacts/service.py` — **only** forwards to **object_storage** (no scalars step logging).
3. **Object storage** stores the blob and project-level metadata in its DB (dedup by hash). See `python/object_storage` project-artifacts domain and `python/backend/src/clients/object_storage/client.py` (`check_project_artifacts`, `upload_project_artifact`, etc.).

```mermaid
sequenceDiagram
  participant SDK
  participant Backend
  participant Obj as object_storage

  SDK->>Backend: POST check (hashes)
  alt hash missing
    SDK->>Backend: POST upload?hash=…
    Backend->>Obj: store blob + metadata (CAS)
  end
```

## Python: use `uv`

**All Python subprojects in this repo use [uv](https://docs.astral.sh/uv/)** for environments, dependency sync, and command execution. Each Python package has its own `pyproject.toml` and typically its own `.venv` when you run commands from that directory.

Work from the package root, for example:

- `cd python/backend && uv run pytest`
- `cd python/backend && uv run uvicorn api.main:app --reload --port 8000`
- `cd python/scalars_service && uv run pytest`
- `cd python/object_storage && uv run pytest`
- `cd python/sdk && uv run pytest`

Do **not** assume a single global `python/backend`-only layout; **scalars_service**, **object_storage**, and **sdk** are first-class packages with their own `uv` workflows.

### SDK version

When shipping SDK changes that should be published or consumed with a pinned version, bump **both** of these and keep them identical:

1. `python/sdk/pyproject.toml` — `[project] version` (package metadata for installs/builds)
2. `python/sdk/src/experiment_tracker_sdk/__init__.py` — `__version__` (runtime; import as `experiment_tracker_sdk.__version__`)

Use [semver](https://semver.org/): **patch** for fixes and small backward-compatible additions, **minor** for larger backward-compatible features, **major** for breaking API changes. Bump the version in the same change set as the SDK feature or fix it describes.

## Frontend: Turborepo and pnpm

- Orchestrated with **Turborepo** (`turbo.json`). Prefer running tasks via Turbo from the repo root when appropriate.
- Inside `apps/web`, use **pnpm** for install and scripts.

Examples:

- From repo root: `pnpm dev` (runs `turbo dev`; install once with `pnpm install` so the local `turbo` package is available).
- From `apps/web`: `pnpm run dev`.
- From `apps/web`: `pnpm run test` runs **Vitest** (unit tests under `src/**/*.test.ts`, e.g. metric display formatting). Metric scalars use **`formatValue`** from `src/lib/metrics/mathjs-metric-format.ts` (mathjs `format`, `notation: 'auto'`; wired through `metric-value-display.ts`; defaults in `src/lib/constants/metric-display.ts`). To run only the mathjs sample test and print strings: `pnpm run test:mathjs-format` (or `pnpm exec vitest run src/lib/metrics/mathjs-format.test.ts`). In-app guide to tuning precision and thresholds: **`/docs/reference/metric-display-formatting`** (`apps/web/content/docs/reference/metric-display-formatting.md`).

For a **single public UI origin** without editing a root `.env`, run **`./scripts/docker-up-public.sh`** from the repository root (see root **`README.md`** → *Custom URL or domain* → *One command without a `.env` file*).

For local development against the backend, set the web env so the UI and BFF target the API (for example `NEXT_PUBLIC_BASE_URL=http://127.0.0.1:8000`). In Docker Compose, the **`web`** service sets **`SERVER_API_BASE_URL=http://backend:8000`** so server-side Route Handlers proxy to the API over the Compose network; **`NEXT_PUBLIC_BASE_URL`** should stay a URL the **browser** can use (typically `http://127.0.0.1:8000` or `http://localhost:8000` on the host port you published for `backend`). For a **custom public URL** (real hostname or HTTPS, not only localhost), set **`NEXT_PUBLIC_BASE_URL`** to that API origin, set **`ALLOWED_ORIGINS`** / **`OBJECT_STORAGE_ALLOWED_ORIGINS`** to your UI origin(s), rebuild **`web`**, and recreate **`backend`** / **`object-storage`** — see the root **`README.md`** section **Custom URL or domain**.

## Backend (main API) quick reference

- **Run server** (from `python/backend`):  
  `uv run uvicorn api.main:app --reload --port 8000 --log-level debug`
- **Database**: PostgreSQL via `DATABASE_URL`, e.g.  
  `export DATABASE_URL="postgresql://myuser:myuser@localhost:5432/experiment_tracker"`  
  (example for local dev; adjust to your environment).
- **Tests**: `uv run pytest -s -v tests/` from `python/backend`.

The HTTP API is mounted with a configurable prefix (see `config/settings.py` / `api_prefix`); client code and the Next.js BFF should stay aligned with that prefix.

### Teams and project members (main API)

- **Teams**: `GET /teams` (paginated list with `canCreateProject` per row), `GET /teams/{team_id}`, `GET /teams/{team_id}/members`, `GET /teams/{team_id}/users/lookup?email=` (requires team manage). Writes: `POST` / `PATCH` on `/teams` (body includes `id` for update), `POST` / `PATCH` / `DELETE` on `/teams/members` (JSON body; member delete uses `userId` + `teamId`).
- **Project members**: `GET /projects/{id}/members` returns `accessSource`: `team` (inherits team role), `override` (per-project permission rows on top of team), or `direct` (invited / project owner). Maintainers with `project.edit` can `PATCH` any **team** member to apply or change a per-project role (writes full project-scoped permission rows; `PermissionService.has_permission` prefers those over team). `DELETE` removes project-scoped rows only—team members then fall back to team inheritance; pure team rows cannot be removed here. Also: `GET /projects/{id}/users/lookup?email=`, `POST` for email invites (`DELETE` JSON body `{ "userId": "..." }`).

### Admin panel and passwords (main API)

- **`ADMIN_PANEL_KEY`**: Defaults to insecure `admin` for local dev. On startup the backend logs a **warning** when the key is still `admin`, and an **info** line (without revealing the value) when a custom key was loaded from `ADMIN_PANEL_KEY`.
- **Admin HTTP API** (no JWT; header **`X-Admin-Key`** must match the configured key): `GET /admin/users?q=&limit=` (default **20**) **`&offset=`** → JSON **`{ items, total, limit, offset }`** (`q` filters email, display name, and user UUID substring), `GET /admin/teams?q=&limit=` **`&offset=`** → same shape (`q` filters team name and description), `POST /admin/users/{user_id}/reset-password` → JSON includes **`temporaryPassword`** once. Storage admin: `GET /admin/storage/buckets` and `GET /admin/storage/scalars` accept **`limit`**, **`offset`**, and optional **`q`** (bucket name / scalar table name filter); responses include **`total`** alongside **`buckets`** or **`tables`**.
- **User password change** (JWT or session cookie auth, not PAT): `POST /users/me/change-password` with JSON **`currentPassword`** and **`newPassword`** (min 8). Web UI: **`/profile`** (collapsible section); legacy **`/profile/password`** redirects there. Bootstrap admin UI: **`/admin`** (stores key in `sessionStorage`).

## Cross-service configuration

Running the full stack locally requires the backend plus whatever URLs you configure for **scalars** and **object storage** services (and their databases/ClickHouse). Those are typically set via environment variables consumed by `python/backend`’s settings and the respective services’ configs—check each package’s `config` or `README` when wiring a new environment.

### Local dev: file descriptors (`Too many open files`)

Canonical write-up (in-app docs): **`/docs/getting-started/file-descriptors`** — source `apps/web/content/docs/getting-started/file-descriptors.md` (errno 24 / 16, `/proc` checks, `run_local_stack.sh` / `uvicorn --reload` when developing, backend/scalars client paths, mitigations).

## Documentation policy for agents

Prefer updating this file or code comments when changing global runbooks; avoid adding new markdown files unless the user asks for them.

For **changing how in-app docs render** (remark/rehype directives, sanitize allowlist, `DocsMarkdown` components), follow and keep in sync **`apps/web/content/docs/contributing/extending-doc-pipeline.md`** (published at `/docs/contributing/extending-doc-pipeline`).

Don't fight bugs! Every time you encounter the same error by accident, research the web and find 3-5 possible ways to fix it. Then choose the most effective solution and implement it.