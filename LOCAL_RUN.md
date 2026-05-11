# Local Run

## Run object storage

### Run minio
```
cd python/object_storage/
docker rm -f minio
docker run -p 9000:9000 -p 9001:9001 --name minio -v minio:/data -e "MINIO_ROOT_USER=admin" -e "MINIO_ROOT_PASSWORD=password" minio/minio server /data --console-address ":9001"
```

### Run object storage
```
cd python/object_storage/
uv run uvicorn object_storage.main:app --reload --port 8002 --log-level debug
```

## Run scalars service

### Run clickhouse
```
docker rm -f /clickhouse-server
docker run --name clickhouse-server --ulimit nofile=262144:262144 -p 8123:8123 -e CLICKHOUSE_USER=default -e CLICKHOUSE_PASSWORD=yourpass -e CLICKHOUSE_DB=metrics -v ./.clickhouse_data:/var/lib/clickhouse/ clickhouse/clickhouse-server
```

### Run scalars service
```
cd python/scalars_service/
uv run uvicorn api.main:app --reload --port 8001 --log-level debug
```

## Run backend
```
cd python/backend/
uv run uvicorn api.main:app --reload --port 8000 --log-level debug
```

## Run frontend
```
cd apps/web/
export NEXT_PUBLIC_BASE_URL=http://127.0.0.1:8000
pnpm run dev
```

## Docker Compose (all services)

From the repository root (see `docker-compose.yml`; Dockerfiles live under `python/*/Dockerfile` and `apps/web/Dockerfile`). A **step-by-step** guide (build/rebuild, `storage/`, UI URL, `down`, network) is in the README under **Docker (full stack) → Full stack: step by step**.

Quick start:

```bash
docker compose up -d --build
```

Optional root `.env` (see `.env.example`) overrides compose defaults; package-level `.env.example` files document local `uv` / `pnpm` runs.

To **force a clean rebuild**, see README **Docker → Force rebuild**. For **hybrid Postgres** setups and extra shutdown detail, see **Docker → Dependencies, startup order, and hybrid setups**.