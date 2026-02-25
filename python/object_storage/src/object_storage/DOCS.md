Technical Task: ML Experiment Storage Service (CAS-based)

## 1. Overview
**Objective:** Develop a high-performance, deduplicated storage microservice for Machine Learning experiments.
**Problem:** Storing ML experiment artifacts (models, datasets, logs) via Git is inefficient. Standard storage solutions lack deduplication, leading to massive storage overhead when experiments share 90% of files (e.g., unchanged datasets or code).
**Solution:** A **Content-Addressable Storage (CAS)** system. Files are addressed by their content hash (SHA-256). Identical files are stored only once, regardless of how many experiments use them.

## 2. Architecture High-Level
*   **Backend:** Python (FastAPI) + PostgreSQL (Metadata) + MinIO (Blob Storage).
*   **Client:** Python SDK (integrated into ML pipelines).
*   **Protocol:** HTTP/REST.

## 3. Data Model
There is two main types of data that are stored in the database:
Objects - blobs that are tracked and deduplicated. Used to store code, data, etc.
Artifacts - snapshots of the objects that are part of an experiment and not tracked. Used to store the state of the experiment at a given point in time like generated images, audio, video, hyperparameters, etc.