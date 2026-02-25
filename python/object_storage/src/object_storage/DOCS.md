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
Project artifacts - blobs that are tracked and deduplicated. Used to store code, data, etc. that are shared between experiments (e.g. different experiments use same code). Also checks hashes of the blobs and returns which ones are missing. 
Snapshots are the part of the project artifacts that are used to create a snapshot of the experiment (because the project artifacts are shared between experiments).
Experiment artifacts - objects that are part of an experiment and not tracked. Used to store the state of the experiment at a given point in time like generated images, audio, video, hyperparameters, etc. Used to push data without any checks. Returns the status of the upload and the path to the blob (calculates the path randomly (via uuid4)).

