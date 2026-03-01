"""HTTP client for object storage service (project-artifacts, experiment-artifacts)."""

import httpx
from fastapi import UploadFile
from uuid import UUID


class ObjectStorageClient:

    ENDPOINTS = {
        "check_project_blobs": lambda project_id: f"/project-artifacts/{project_id}/check",
        "upload_project_blob": lambda project_id, blob_hash: f"/project-artifacts/{project_id}/upload?hash={blob_hash}",
        "download_project_blob": lambda project_id, blob_hash: f"/project-artifacts/{project_id}/blobs/{blob_hash}",
        "create_project_snapshot": lambda project_id: f"/project-artifacts/{project_id}/snapshots",
        "download_project_snapshot": lambda project_id, snapshot_id: f"/project-artifacts/{project_id}/snapshots/{snapshot_id}/download",
        "delete_project_blob": lambda project_id, blob_hash: f"/project-artifacts/{project_id}/blobs/{blob_hash}",
        "delete_project": lambda project_id: f"/project-artifacts/{project_id}",
        "upload_experiment_artifact": lambda experiment_id: f"/experiment-artifacts/{experiment_id}/upload",
        "download_experiment_artifact": lambda experiment_id, path: f"/experiment-artifacts/{experiment_id}/download?path={path}",
        "delete_experiment_artifact": lambda experiment_id, path: f"/experiment-artifacts/{experiment_id}?path={path}",
        "delete_experiment_artifacts": lambda experiment_id: f"/experiment-artifacts/experiments/{experiment_id}",
    }

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def check_project_blobs(self, project_id: UUID, hashes: list[str]) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{self.ENDPOINTS['check_project_blobs'](project_id)}",
                json=hashes,
            )
            response.raise_for_status()
            return response.json()

    async def upload_project_blob(
        self, project_id: UUID, blob_hash: str, upload: UploadFile
    ) -> dict:
        upload.file.seek(0)
        files = {
            "file": (
                upload.filename,
                upload.file,
                upload.content_type or "application/octet-stream",
            )
        }
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}{self.ENDPOINTS['upload_project_blob'](project_id, blob_hash)}",
                params={"hash": blob_hash},
                files=files,
            )
            response.raise_for_status()
            return response.json()

    async def download_project_blob(self, project_id: UUID, blob_hash: str) -> bytes:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.get(
                f"{self.base_url}{self.ENDPOINTS['download_project_blob'](project_id, blob_hash)}",
            )
            response.raise_for_status()
            return response.content

    async def create_project_snapshot(self, project_id: UUID, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{self.ENDPOINTS['create_project_snapshot'](project_id)}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def download_project_snapshot(
        self, project_id: UUID, snapshot_id: UUID
    ) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{self.ENDPOINTS['download_project_snapshot'](project_id, snapshot_id)}",
            )
            response.raise_for_status()
            return response

    async def delete_project_blob(self, project_id: UUID, blob_hash: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}{self.ENDPOINTS['delete_project_blob'](project_id, blob_hash)}",
            )
            response.raise_for_status()
            return response.json()

    async def delete_project(self, project_id: UUID) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}{self.ENDPOINTS['delete_project'](project_id)}",
            )
            response.raise_for_status()
            return response.json()

    async def upload_experiment_artifact(
        self, experiment_id: UUID, file: UploadFile
    ) -> dict:
        file.file.seek(0)
        files = {
            "file": (
                file.filename,
                file.file,
                file.content_type or "application/octet-stream",
            )
        }
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}{self.ENDPOINTS['upload_experiment_artifact'](experiment_id)}",
                files=files,
            )
            response.raise_for_status()
            return response.json()

    async def download_experiment_artifact(
        self, experiment_id: UUID, path: str
    ) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{self.ENDPOINTS['download_experiment_artifact'](experiment_id, path)}",
            )
            response.raise_for_status()
            return response

    async def delete_experiment_artifact(self, experiment_id: UUID, path: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}{self.ENDPOINTS['delete_experiment_artifact'](experiment_id, path)}",
            )
            response.raise_for_status()
            return response.json()

    async def delete_experiment_artifacts(self, experiment_id: UUID) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}{self.ENDPOINTS['delete_experiment_artifacts'](experiment_id)}",
            )
            response.raise_for_status()
            return response.json()
