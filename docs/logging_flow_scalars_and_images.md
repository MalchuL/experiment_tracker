# Logging Flow: Scalars and Images

This document describes how scalar and image data is logged end-to-end:
- SDK method calls
- backend/scalars_service/object_storage interactions
- HTTP request sequence

## 1) Scalars Logging Flow

### High-level method flow

1. Training code calls:
   - `ExpTracker.add_scalar(...)`
   - or multiple calls for the same step.
2. SDK batches values per step in memory:
   - `ExpTracker._current_values`
3. On step change (or `flush()/close()`), SDK enqueues:
   - `API.scalars.log_scalar(...)`
4. `ExperimentTrackerClient` sends request to backend:
   - `POST /api/scalars/log/{experiment_id}`
5. Backend (`domain/scalars`) resolves `project_id`, checks permissions, and forwards to scalars service:
   - `POST {SCALARS_SERVICE_URL}/scalars/log/{project_id}/{experiment_id}`
6. Scalars service writes into per-project ClickHouse table:
   - `scalars_{project_id}`

### HTTP sequence

```mermaid
sequenceDiagram
    participant Train as Training Script
    participant SDK as SDK (ExpTracker)
    participant BE as Backend API
    participant SS as Scalars Service
    participant CH as ClickHouse

    Train->>SDK: add_scalar(tag, value, step)
    SDK->>SDK: buffer values for current step
    SDK->>BE: POST /api/scalars/log/{experiment_id}
    BE->>BE: resolve project_id + RBAC check
    BE->>SS: POST /scalars/log/{project_id}/{experiment_id}
    SS->>CH: INSERT row into scalars_{project_id}
    CH-->>SS: OK
    SS-->>BE: {status:"logged"}
    BE-->>SDK: {status:"logged"}
```

## 2) Images Logging Flow

### High-level method flow

1. Training code calls:
   - `ExpTracker.add_image(tag, img, step)`
2. SDK converts image to PNG bytes:
   - accepts `PIL.Image` or `numpy.ndarray`
   - normalizes/casts to uint8
   - converts layout to RGB/RGBA
3. SDK computes content hash:
   - `sha256(content_bytes)` => `blob_hash`
4. SDK checks if blob already exists:
   - `POST /api/blobs/check`
5. If missing, SDK uploads blob:
   - `POST /api/blobs/upload?hash={blob_hash}` (multipart)
6. SDK logs image metadata as object row:
   - `POST /api/objects/log/{experiment_id}`
7. Backend (`domain/objects`) resolves `project_id`, checks permissions, and forwards to scalars service:
   - `POST {SCALARS_SERVICE_URL}/objects/log/{project_id}/{experiment_id}`
8. Scalars service writes metadata row into:
   - `objects_{project_id}` (ClickHouse)

### HTTP sequence

```mermaid
sequenceDiagram
    participant Train as Training Script
    participant SDK as SDK (ExpTracker)
    participant FE as Backend API
    participant OS as Object Storage Service
    participant SS as Scalars Service
    participant CH as ClickHouse

    Train->>SDK: add_image(tag, image, step)
    SDK->>SDK: convert to PNG bytes + sha256 hash
    SDK->>FE: POST /api/blobs/check [hash]
    FE->>OS: POST /blobs/check [hash]
    OS-->>FE: {missing:[...]}
    FE-->>SDK: {missing:[...]}

    alt hash missing
      SDK->>FE: POST /api/blobs/upload?hash=...
      FE->>OS: POST /blobs/upload?hash=... (multipart)
      OS-->>FE: {status:"ok"|"exists"}
      FE-->>SDK: {status:"ok"|"exists"}
    end

    SDK->>FE: POST /api/objects/log/{experiment_id}
    FE->>FE: resolve project_id + RBAC check
    FE->>SS: POST /objects/log/{project_id}/{experiment_id}
    SS->>CH: INSERT into objects_{project_id}
    CH-->>SS: OK
    SS-->>FE: {status:"logged"}
    FE-->>SDK: {status:"logged"}
```

## Notes

- Blob content is stored in object storage (S3/MinIO).
- Only lightweight metadata is stored in ClickHouse (`objects_{project_id}`), which keeps UI queries fast.
- For images, `path` currently stores the blob hash reference.
