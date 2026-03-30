# Experiment Artifacts API

This document explains how experiment artifact storage works in `object_storage`,
including tracked and untracked flows, service methods, and HTTP endpoints.

## Overview

Experiment artifact storage is **hash-based** and split into two modes:

- **Untracked artifacts**: stored in object storage bucket only. No DB row in
  `experiment_blobs`.
- **Tracked artifacts**: stored in object storage and persisted in DB
  (`experiment_blobs`) with metadata such as `file_path`, `mime_type`, and `size`.

Both modes store blob bytes by **artifact hash** (not by path key).

## Core Components

- Service: `object_storage.domain.experiment_artifacts_storage.service.ArtifactsStorageService`
- Repository: `object_storage.domain.experiment_artifacts_storage.repository.ExperimentArtifactsRepository`
- Bucket service: `object_storage.domain.buckets.service.BucketRegistryService`
- DB models: `object_storage.db.models.ExperimentBlob`, `object_storage.db.models.Bucket`

## Bucket and Hash Rules

- Bucket name format:
  - project scope: `project-<project_id>`
  - experiment scope: short S3-safe format `prj-<project_hex16>-exp-<experiment_hex16>`
- Hash validation in `check_hash()` accepts `^[0-9a-fA-F]{4,64}$`.
- `BucketRegistryService.upload_blob()` computes SHA-256 while streaming upload.
  - If the caller provides `hash`, that hash is used as object key.
  - Otherwise computed hash is used.

## Service Methods

### `check_hash(hash: str) -> None`

Validates incoming hash format. Raises `HashNotValidError` when invalid.

### `upload_artifact_and_forget(project_id, experiment_id, upload, hash=None) -> UntrackedUploadArtifactResponseDTO`

Stores artifact bytes only:

1. chooses `artifact_hash = hash or uuid4().hex`
2. validates hash
3. ensures `(project_id, experiment_id)` bucket exists
4. uploads bytes under `artifact_hash`
5. commits bucket size metadata
6. returns `{ hash, size }`

No `ExperimentBlob` row is created.

### `upload_artifact_and_track(project_id, experiment_id, upload, hash=None, path=None) -> TrackedUploadArtifactResponseDTO`

Stores artifact and tracks DB metadata:

1. chooses and validates `artifact_hash`
2. ensures experiment bucket exists
3. uploads bytes under hash
4. resolves `file_path = normalize_path(path or upload.filename)`
5. validates `file_path` using `validate_relative_path`
6. inserts `ExperimentBlob` with hash/path/mime/size
7. commits repository
8. returns tracked DTO `{ id, hash, file_path, mime_type, size }`

### `list_artifacts(project_id, experiment_id, limit=100, offset=0) -> list[TrackedUploadArtifactResponseDTO]`

Lists tracked artifacts from `experiment_blobs` for the pair
`(project_id, experiment_id)` with pagination.

### `get_artifact_stream(project_id, experiment_id, artifact_hash, tracked=False) -> ArtifactStreamResponseDTO`

Fetches streamed content by hash:

- `tracked=False`:
  - streams object directly from bucket
  - returns fallback metadata (`application/octet-stream`, no filename/path)
- `tracked=True`:
  - requires matching `ExperimentBlob`
  - includes DB metadata (`size`, `mime_type`, `filename`, `file_path`)
  - raises `ValueError` if tracked row is missing

### `delete_artifact(project_id, experiment_id, artifact_hash) -> DeleteArtifactResponseDTO`

Deletes tracked DB row by hash and removes hash-keyed object from bucket.
Returns `{ deleted: true }`.

### `delete_experiment(project_id, experiment_id) -> DeleteExperimentArtifactsResponseDTO`

Deletes the experiment bucket and all tracked rows for this experiment.
Returns `{ deleted_count: 0 }` currently.

## HTTP Endpoints

Router prefix: `/experiment-artifacts`

- `POST /projects/{project_id}/experiments/{experiment_id}/upload-untracked`
  - query: `hash` (optional)
  - multipart: `file`
  - response: `UntrackedUploadArtifactResponseDTO`

- `POST /projects/{project_id}/experiments/{experiment_id}/upload-tracked`
  - query: `hash` (optional), `path` (optional)
  - multipart: `file`
  - response: `TrackedUploadArtifactResponseDTO`

- `GET /projects/{project_id}/experiments/{experiment_id}/artifacts`
  - query: `limit` (default 100), `offset` (default 0)
  - response: `list[TrackedUploadArtifactResponseDTO]`

- `GET /projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}`
  - query: `tracked` (default `false`)
  - response: streamed bytes (`StreamingResponse`)

- `DELETE /projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}`
  - response: `DeleteArtifactResponseDTO`

- `DELETE /projects/{project_id}/experiments/{experiment_id}`
  - response: `DeleteExperimentArtifactsResponseDTO`

## Tracked vs Untracked Usage Guidance

- Use **untracked upload** for transient/large training files (for example
  generated samples, temporary media) where DB manifest tracking is not needed.
- Use **tracked upload** for reproducibility-critical artifacts (for example
  configs, model files, diffs) where DB metadata must be queryable and listable.

