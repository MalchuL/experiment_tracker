# Object Storage Service Architecture

## Purpose
This service provides **content-addressable storage (CAS)** for ML experiment
artifacts. Files are stored by the SHA-256 hash of their content, so identical
files are stored once and reused across snapshots.

## What It Can Do
- Store large files (streaming upload) addressed by content hash.
- Deduplicate files across experiments.
- Create immutable **snapshots** that map original paths to hashes.
- Stream a snapshot back as a ZIP archive (reconstructed from hashes).

## What It Requires
- **Python 3.13+** with `uv` (see `pyproject.toml`).
- **PostgreSQL** for metadata (experiments, snapshots, blobs).
- **S3-compatible object storage** for blob bytes:
  - **AWS S3** by default (via `boto3`).
  - **MinIO** supported as an alternate backend.

## High-Level Flow (CAS)
1. **Client scans files**, computes SHA-256 hashes.
2. **/blobs/check** returns which hashes are missing.
3. **/blobs/upload** streams missing blobs; server verifies hash.
4. **/snapshots** stores a manifest (`path -> hash, size`) tied to an experiment.
5. Optional: **/snapshots/{id}/download** reconstructs a ZIP from hashes.

## Core Components

### API Layer
Located in `src/object_storage/api/` and delegates to the domain controller.
- Routes: `/blobs/check`, `/blobs/upload`, `/snapshots`, `/snapshots/{id}/download`
- Validation and request parsing are handled by DTOs.

### Domain Layer
Located in `src/object_storage/domain/object_storage/`.
- **controller.py**: FastAPI endpoints, dependency wiring.
- **service.py**: CAS business logic (hash checks, uploads, snapshots).
- **repository.py**: database access for blobs/experiments/snapshots.
- **dto.py**: request/response schemas.
- **mapper.py**: mapping helpers between DTOs and storage shapes.

### Storage Layer
Located in `src/object_storage/storage/`.
- **S3 backend (default)**: `S3Storage` using `boto3`.
- **MinIO backend**: `MinioStorage` using `minio` SDK.
- **get_storage()** selects backend via config.

### Database Layer
Located in `src/object_storage/db/`.
- `models.py`: SQLAlchemy models for `experiments`, `snapshots`, `blobs`.
- `database.py`: async session and table initialization.

## Data Model
- **experiments**: `id`, `name`, `created_at`
- **snapshots**: `id`, `experiment_id`, `created_at`, `manifest` (JSONB)
- **blobs**: `hash`, `size`, `ref_count`, `created_at`

## API Endpoints (Summary)
- `POST /blobs/check`  
  Input: list of hashes  
  Output: list of missing hashes

- `POST /blobs/upload`  
  Input: multipart file + `hash` query param  
  Output: upload status

- `POST /snapshots`  
  Input: experiment name + list of files (`path`, `hash`, `size`)  
  Output: snapshot id

- `GET /snapshots/{id}/download`  
  Output: ZIP stream of snapshot files

## Configuration
Configuration is loaded from environment variables (see `src/object_storage/config.py`).

### Storage Selection
- `storage_backend`: `s3` (default) or `minio`

### S3 Settings (Default Backend)
- `s3_endpoint_url` (optional; set for MinIO or local S3-compatible)
- `s3_region`
- `s3_access_key_id`
- `s3_secret_access_key`
- `s3_bucket`

### MinIO Settings (Alternate Backend)
- `minio_endpoint`
- `minio_access_key`
- `minio_secret_key`
- `minio_secure`
- `minio_bucket`

### Database
- `database_url`

## Startup Lifecycle
On application startup (`lifespan` in `main.py`):
1. Database tables are created if missing.
2. The configured storage bucket is ensured.

## Notes for Contributors
- Keep business logic in the **service** layer.
- Use **repository** for DB access only.
- Storage clients should implement the `StorageBackend` protocol.
