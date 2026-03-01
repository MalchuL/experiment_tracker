# Artifacts Architecture and Build Guide

## Architecture

Artifacts are experiment-linked files (images, videos, audio, text, point clouds) with step-based metadata, similar to scalars. The backend forwards artifact requests to two external services:

- **scalars_service** — stores artifact metadata (artifacts_info) in ClickHouse
- **object_storage** — stores binary blobs in S3/MinIO (project-scoped CAS, experiment bucket)

```mermaid
flowchart TB
    subgraph clients [Clients]
        SDK[SDK]
        Web[Frontend]
    end

    subgraph backend [Backend API]
        ExpArtifacts[/experiment-artifacts]
        ProjArtifacts[/project-artifacts]
        ObjStorageClient[ObjectStorageClient]
        ArtifactsInfoClient[ArtifactsInfoClient]
    end

    subgraph services [External Services]
        Scalars[scalars_service]
        ObjStorage[object_storage]
    end

    SDK -->|log, upload, download| ExpArtifacts
    SDK -->|get, download blobs| ProjArtifacts
    Web -->|get metadata, download| ProjArtifacts

    ExpArtifacts --> ArtifactsInfoClient
    ExpArtifacts --> ObjStorageClient
    ProjArtifacts --> ArtifactsInfoClient
    ProjArtifacts --> ObjStorageClient
    ArtifactsInfoClient --> Scalars
    ObjStorageClient --> ObjStorage
```

**Flow for artifact upload:**
1. SDK or client calls `POST /api/project-artifacts/{project_id}/log/{experiment_id}` with file + metadata
2. Backend checks permissions, forwards blob to object_storage (if missing), logs metadata to scalars_service
3. Metadata stored in scalars_service; blobs stored in object_storage

**Flow for artifact download:**
1. Client calls `GET /api/project-artifacts/{project_id}/blobs/{blob_hash}`
2. Backend checks permissions, forwards request to object_storage
3. Blob streamed back to client

---

## API Reference

### experiment_artifacts (`/api/experiment-artifacts`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/{experiment_id}/log` | Upload file to experiment bucket and log metadata (multipart) |
| POST | `/{experiment_id}/log_metadata` | Log artifact metadata only (file already in storage) |
| GET | `/{experiment_id}/download?path=` | Download artifact by path from experiment bucket |
| DELETE | `/{experiment_id}?path=` | Delete one artifact by path |
| DELETE | `/experiments/{experiment_id}` | Delete all artifacts for an experiment |

### project_artifacts (`/api/project-artifacts`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/{project_id}/log/{experiment_id}` | Upload file to project CAS and log artifact metadata (multipart) |
| GET | `/{project_id}/get` | Get artifacts metadata for a project |
| POST | `/{project_id}/check` | Check which blob hashes are missing from CAS |
| POST | `/{project_id}/upload?hash=` | Upload blob to project CAS |
| GET | `/{project_id}/blobs/{blob_hash}` | Download blob by hash |
| POST | `/{project_id}/snapshots` | Create snapshot from CAS blobs |
| GET | `/{project_id}/snapshots/{snapshot_id}/download` | Download snapshot as ZIP |
| DELETE | `/{project_id}/blobs/{blob_hash}` | Delete blob from CAS |
| DELETE | `/{project_id}` | Delete project (all blobs and snapshots) |

### Query Parameters for GET /api/project-artifacts/{project_id}/get

| Param | Type | Description |
|-------|------|-------------|
| experiment_id | list[UUID] | Filter by experiment IDs |
| artifact_type | list[str] | Filter by type (image, video, audio, text, point_cloud_3d) |
| artifact_name | list[str] | Filter by artifact name |
| start_time | datetime | Start of time range |
| end_time | datetime | End of time range |
| format | str | Use `format=objects` for frontend compatibility (returns objects/object_type) |

---

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `SCALARS_SERVICE_URL` | scalars_service base URL | `http://127.0.0.1:8001/api` |
| `OBJECT_STORAGE_SERVICE_URL` | object_storage base URL | `http://127.0.0.1:8010/api` |
| `DATABASE_URL` | PostgreSQL connection string | (see backend README) |

If either `SCALARS_SERVICE_URL` or `OBJECT_STORAGE_SERVICE_URL` is unset, artifact features are disabled (NoOp services).

### object_storage Service

| Variable | Description | Default |
|----------|-------------|---------|
| `storage_backend` | `s3` or `minio` | `s3` |
| `s3_endpoint_url` | S3 endpoint (optional for AWS) | — |
| `s3_access_key_id` | S3 access key | — |
| `s3_secret_access_key` | S3 secret key | — |
| `s3_bucket` | Bucket name | `ml-blobs` |
| `minio_endpoint` | MinIO endpoint | `localhost:9000` |
| `minio_access_key` | MinIO access key | `minio` |
| `minio_secret_key` | MinIO secret key | `minio123` |

### scalars_service

See `python/scalars_service/README.md` for configuration.

---

## Build and Run

### 1. Backend

```bash
cd python/backend
export DATABASE_URL="postgresql://user:pass@localhost:5432/experiment_tracker"
export SCALARS_SERVICE_URL="http://127.0.0.1:8001/api"
export OBJECT_STORAGE_SERVICE_URL="http://127.0.0.1:8010/api"
uv run uvicorn api.main:app --reload --port 8000
```

### 2. scalars_service

```bash
cd python/scalars_service
# Configure ClickHouse, then:
uv run uvicorn app.main:app --reload --port 8001
```

### 3. object_storage

```bash
cd python/object_storage
# Configure S3/MinIO, then:
uv run python -m object_storage.main
# Runs on port 8010 by default
```

### 4. Frontend

```bash
export NEXT_PUBLIC_BASE_URL=http://127.0.0.1:8000
cd apps/web && pnpm run dev
```

---

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| Backend | 8000 | API gateway, auth, RBAC, forwards to scalars + object_storage |
| scalars_service | 8001 | Scalars + artifact metadata (ClickHouse) |
| object_storage | 8010 | Blob storage (S3/MinIO, project-scoped CAS, experiment bucket) |

---

## Migration Notes

- The monolithic `/api/artifacts/*` API has been split into:
  - **experiment_artifacts** (`/api/experiment-artifacts`) — log, upload, download, delete per experiment
  - **project_artifacts** (`/api/project-artifacts`) — get metadata, blobs, snapshots, delete project
- Blob download: use `/api/project-artifacts/{project_id}/blobs/{blob_hash}`.
- For frontend compatibility, use `?format=objects` on the project-artifacts get endpoint to receive `objects`/`object_type` instead of `artifacts_info`/`artifact_type`.
