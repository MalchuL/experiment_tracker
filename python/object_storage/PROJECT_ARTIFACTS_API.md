# Project artifacts (CAS) API

Project-scoped content-addressable storage: blobs are keyed by **SHA-256 hash** in object storage. Snapshot manifests still use **logical paths** so ZIP downloads can reconstruct directory layout.

## Components

- Service: `object_storage.domain.project_artifacts_storage.service.ObjectStorageService`
- Repository: `object_storage.domain.project_artifacts_storage.repository.ObjectStorageRepository`
- Blob metadata model: `object_storage.db.models.ProjectBlob` (table `tracked_blobs`)
- Bucket lifecycle: `object_storage.domain.buckets.service.BucketRegistryService` with `experiment_id=None` for the project bucket

## Bucket registry (project scope)

Project CAS uses the same `BucketRegistryService` as experiment artifacts, but only the **project-level** bucket row: `experiment_id` is **NULL** in Postgres. The `buckets` table uses a surrogate `id` primary key and partial unique indexes so there is at most one project-scoped row per `project_id` and at most one row per `(project_id, experiment_id)` when `experiment_id` is set. Bucket name remains `project-{project_id}` via `project_experiment_bucket_name(project_id, None)`.

The registry:

- ensures the bucket exists in DB and in object storage,
- increments/decrements `buckets.size` on upload/delete,
- lists and deletes all objects before removing a bucket when tearing down.

## Storage keys vs manifest paths

- **Object storage**: keys are derived from the blob hash (see `StorageBackend.put_blob` / `blobs/…` layout in S3/MinIO clients).
- **Snapshots**: each manifest entry has `path` (relative, safe) and `hash` (64-char hex). ZIP build reads bytes by hash and writes them under `path` inside the archive.

## Service methods (summary)

| Method | Role |
|--------|------|
| `check_project_blobs` | Ensures project bucket; returns hashes not yet in `ProjectBlob` metadata. |
| `upload_project_blob` | Verifies upload hash, stores via bucket registry, inserts `ProjectBlob`. |
| `create_project_snapshot` | Validates paths; ensures all hashes exist; stores manifest + bumps `ref_count`. |
| `delete_project_snapshot` | Decrements refs; deletes storage + rows for unreferenced blobs; removes snapshot row. |
| `prepare_project_snapshot_download` | Builds temp ZIP from manifest (hash lookup + path names). |
| `get_project_blob_stream` | Streams one blob by hash if metadata exists. |
| `delete_project_blob` | Fails if `ref_count > 0`; removes metadata and object via bucket registry. |
| `delete_project` | Deletes all buckets for the project (registry), all `ProjectBlob` rows, all snapshots. |

## HTTP routes

See `object_storage.domain.project_artifacts_storage.controller`: prefix `/project-artifacts`, unchanged contract (hash query on upload, hash in path for download/delete).
