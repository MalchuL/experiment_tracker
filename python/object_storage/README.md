# Object Storage Service

FastAPI service providing content-addressable storage (CAS) backed by RustFS and Postgres.

Detailed API behavior for experiment artifacts (tracked vs untracked, hash-based
storage, service methods, and endpoints):

- `python/object_storage/EXPERIMENT_ARTIFACTS_API.md`

Project-wide CAS (snapshots, `ProjectBlob` metadata, bucket registry for the project bucket):

- `python/object_storage/PROJECT_ARTIFACTS_API.md`

## Local Development

### Setup Database

`sudo -u postgres psql` - Opens default postgres user
`ALTER ROLE myuser SUPERUSER;` - Grant permission to create extension
`CREATE DATABASE object_storage WITH OWNER = myuser;`
`export DATABASE_URL="postgresql://myuser:myuser@localhost:5432/object_storage"` - Create db for specific user

### TL;DR
```
cd python/object_storage
cp .env.example .env
docker rm -f rustfs
docker run -p 9000:9000 -p 9001:9001 --name rustfs -v rustfs:/data -e "RUSTFS_ACCESS_KEY=admin" -e "RUSTFS_SECRET_KEY=password" rustfs/rustfs:latest /data
uv run uvicorn object_storage.main:app --reload --port 8002 --log-level debug
```

### Run the service
```
uv run uvicorn object_storage.main:app --reload --port 8002 --log-level debug
```

## Tests (isolated with testcontainers)

Tests use ephemeral Docker containers for Postgres and RustFS, then override
`DATABASE_URL` and `S3_*` environment variables at runtime. This prevents
overlap with local development services and does not persist test data.

Run:
```
cd python/object_storage
uv sync --extra dev
uv run pytest -q
```
