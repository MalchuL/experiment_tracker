# Local Run

This guide covers manual local development without Docker Compose. For a one-command full stack, use the root `docker-compose.yml` flow documented in `README.md`.

## Setup

### Backend Database

The backend stores users, teams, projects, experiments, reports, hypotheses, and permissions in PostgreSQL.

```bash
sudo -u postgres psql
ALTER ROLE myuser SUPERUSER;
CREATE DATABASE experiment_tracker WITH OWNER = myuser;
export DATABASE_URL="postgresql+asyncpg://myuser:myuser@localhost:5432/experiment_tracker"
```

Copy the backend env template and adjust values as needed:

```bash
cd python/backend
cp .env.example .env
```

Important local values from [python/backend/.env.example](python/backend/.env.example):

```env
DATABASE_URL="postgresql+asyncpg://myuser:myuser@localhost:5432/experiment_tracker"
SCALARS_SERVICE_URL=http://127.0.0.1:8001/api
OBJECT_STORAGE_SERVICE_URL=http://127.0.0.1:8002/api
ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
```

### Object Storage Database

The object storage service stores bucket and artifact metadata in PostgreSQL. File bytes live in MinIO or another S3-compatible store.

```bash
sudo -u postgres psql
ALTER ROLE myuser SUPERUSER;
CREATE DATABASE object_storage WITH OWNER = myuser;
export DATABASE_URL="postgresql+asyncpg://myuser:myuser@localhost:5432/object_storage"
```

Copy the object storage env template and adjust values as needed:

```bash
cd python/object_storage
cp .env.example .env
```

Important local values from [python/object_storage/.env.example](python/object_storage/.env.example):

```env
DATABASE_URL="postgresql+asyncpg://myuser:myuser@localhost:5432/object_storage"
S3_ENDPOINT_URL="http://localhost:9000"
S3_REGION="us-east-1"
S3_ACCESS_KEY_ID="admin"
S3_SECRET_ACCESS_KEY="password"
S3_BUCKET="ml-blobs"
ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
```

### Scalars Service

The scalars service stores time-series metrics and step-level artifact metadata in ClickHouse. Redis is optional cache infrastructure for this service.

Copy the scalars env template and adjust values as needed:

```bash
cd python/scalars_service
cp .env.example .env
```

Important local values from [python/scalars_service/.env.example](python/scalars_service/.env.example):

```env
CLICKHOUSE_URL=http://default:yourpass@localhost:8123/default
REDIS_URL=redis://localhost:6379/0
```

If you run Redis from the root Compose stack, its default host port is `6380`, so use:

```env
REDIS_URL=redis://localhost:6380/0
```

### Frontend

The Next.js frontend calls the backend API from the browser and through server-side route handlers.

```bash
cd apps/web
cp .env.example .env
```

Important local values from [apps/web/.env.example](apps/web/.env.example):

```env
PUBLIC_API_BASE_URL=http://127.0.0.1:8000
SERVER_API_BASE_URL=http://127.0.0.1:8000
```

Install frontend dependencies once from the repo root or `apps/web`:

```bash
pnpm install
```

## Run Everything

The canonical local run commands live in [run_local_stack.sh](run_local_stack.sh). The script opens separate terminal windows for MinIO, object storage, ClickHouse, scalars service, backend, and frontend.

```bash
./run_local_stack.sh
```

If the script is not executable:

```bash
bash run_local_stack.sh
```

## Run Services Individually

These commands mirror [run_local_stack.sh](run_local_stack.sh). Run each long-lived process in a separate terminal.

### MinIO

```bash
cd python/object_storage
docker rm -f minio
docker run -p 9000:9000 -p 9001:9001 --name minio -v minio:/data -e "MINIO_ROOT_USER=admin" -e "MINIO_ROOT_PASSWORD=password" minio/minio server /data --console-address ":9001"
```

MinIO API: `http://localhost:9000`

MinIO console: `http://localhost:9001`

### Object Storage Service

```bash
cd python/object_storage
uv run uvicorn object_storage.main:app --reload --port 8002 --log-level debug
```

Object storage API: `http://127.0.0.1:8002/api`

### ClickHouse

```bash
docker rm -f clickhouse-server
docker run --name clickhouse-server --ulimit nofile=262144:262144 -p 8123:8123 -e CLICKHOUSE_USER=default -e CLICKHOUSE_PASSWORD=yourpass -e CLICKHOUSE_DB=metrics -v ./.clickhouse_data:/var/lib/clickhouse/ clickhouse/clickhouse-server
```

ClickHouse URL for `.env`: `http://default:yourpass@localhost:8123/default`

### Scalars Service

```bash
cd python/scalars_service
uv run uvicorn api.main:app --reload --port 8001 --log-level debug
```

Scalars API: `http://127.0.0.1:8001/api`

### Backend

```bash
cd python/backend
uv run uvicorn api.main:app --reload --port 8000 --log-level debug
```

Backend API: `http://127.0.0.1:8000/api`

Interactive API docs are usually available at `http://127.0.0.1:8000/docs`.

### Frontend

```bash
cd apps/web
export PUBLIC_API_BASE_URL=http://127.0.0.1:8000
pnpm run dev
```

Frontend UI: `http://localhost:3000`

## SDK Local Use

The SDK is not a long-running service. Use it from training code or scripts after the backend is running.

```bash
cd python/sdk
uv pip install -e .
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
experiment-tracker ping
experiment-tracker whoami
```

For development tests:

```bash
cd python/sdk
uv pip install -e ".[dev]"
uv run pytest
```

## Docker Compose Alternative

From the repository root, Docker Compose starts all services and their dependencies:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Optional root `.env` values are documented in [.env.example](.env.example). The full Docker guide is in [README.md](README.md).
