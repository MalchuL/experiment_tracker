"""HTTP client for object storage service (project-artifacts, experiment-artifacts)."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import httpx
from fastapi import UploadFile

from .dto import (
    CheckProjectArtifactsResponseDTO,
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadExperimentArtifactResponseDTO,
    UploadProjectArtifactResponseDTO,
)


class ObjectStorageClient:
    """HTTP client for object storage service (project-artifacts, experiment-artifacts).

    This client is used to check, upload, download, create snapshots, delete project and experiment artifacts.

    Args:
        base_url: The base URL of the object storage service.
    """

    ENDPOINTS: dict[str, Any] = {
        "check_project_artifacts": lambda project_id: f"/project-artifacts/{project_id}/check",
        "upload_project_artifact": lambda project_id, artifact_hash: f"/project-artifacts/{project_id}/upload?hash={artifact_hash}",
        "download_project_artifact": lambda project_id, artifact_hash: f"/project-artifacts/{project_id}/artifacts/{artifact_hash}",
        "create_project_snapshot": lambda project_id: f"/project-artifacts/{project_id}/snapshots",
        "download_project_snapshot": lambda project_id, snapshot_id: f"/project-artifacts/{project_id}/snapshots/{snapshot_id}/download",
        "delete_project_artifact": lambda project_id, artifact_hash: f"/project-artifacts/{project_id}/artifacts/{artifact_hash}",
        "delete_project": lambda project_id: f"/project-artifacts/{project_id}",
        "upload_experiment_artifact": lambda experiment_id: f"/experiment-artifacts/{experiment_id}/upload",
        "download_experiment_artifact": lambda experiment_id, path: f"/experiment-artifacts/{experiment_id}/download?path={path}",
        "delete_experiment_artifact": lambda experiment_id, path: f"/experiment-artifacts/{experiment_id}?path={path}",
        "delete_experiment_artifacts": lambda experiment_id: f"/experiment-artifacts/experiments/{experiment_id}",
    }

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def check_project_artifacts(
        self, project_id: UUID, hashes: list[str]
    ) -> CheckProjectArtifactsResponseDTO:
        """Check if the project artifacts exist in the object storage.

        Args:
            project_id: The ID of the project.
            hashes: The hashes of the project artifacts.

        Returns:
            The response from the object storage.
        """
        response = await self._request(
            "POST",
            self.ENDPOINTS["check_project_artifacts"](project_id),
            json_payload=hashes,
        )
        return CheckProjectArtifactsResponseDTO.model_validate(response)

    async def upload_project_artifact(
        self, project_id: UUID, artifact_hash: str, upload: UploadFile
    ) -> UploadProjectArtifactResponseDTO:
        """Upload a project artifact to the object storage.

        Args:
            project_id: The ID of the project.
            artifact_hash: The hash of the project artifact.
            upload: The upload file.
        """
        upload.file.seek(0)
        files = {
            "file": (
                upload.filename,
                upload.file,
                upload.content_type or "application/octet-stream",
            )
        }
        response = await self._request(
            "POST",
            self.ENDPOINTS["upload_project_artifact"](project_id, artifact_hash),
            params={"hash": artifact_hash},
            files=files,
            timeout=None,
        )
        return UploadProjectArtifactResponseDTO.model_validate(response)

    async def download_project_artifact(
        self, project_id: UUID, artifact_hash: str
    ) -> bytes:
        """Download a project artifact from the object storage.

        Args:
            project_id: The ID of the project.
            artifact_hash: The hash of the project artifact.

        Returns:
            The response from the object storage.
        """
        response = await self._request(
            "GET",
            self.ENDPOINTS["download_project_artifact"](project_id, artifact_hash),
            timeout=None,
            return_bytes=True,
        )
        return cast(bytes, response)

    async def create_project_snapshot(
        self, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        """Create a project snapshot in the object storage.

        Args:
            project_id: The ID of the project.
            payload: The payload to create the project snapshot.

        Returns:
            The response from the object storage.
        """
        response = await self._request(
            "POST",
            self.ENDPOINTS["create_project_snapshot"](project_id),
            json_payload=payload.model_dump(mode="json"),
        )
        return SnapshotCreateResponseDTO.model_validate(response)

    async def download_project_snapshot(
        self, project_id: UUID, snapshot_id: UUID
    ) -> httpx.Response:
        """Download a project snapshot from the object storage.

        Args:
            project_id: The ID of the project.
            snapshot_id: The ID of the project snapshot.

        Returns:
            The response from the object storage.
        """
        response = await self._request(
            "GET",
            self.ENDPOINTS["download_project_snapshot"](project_id, snapshot_id),
            return_response=True,
        )
        return cast(httpx.Response, response)

    async def delete_project_artifact(
        self, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO:
        response = await self._request(
            "DELETE",
            self.ENDPOINTS["delete_project_artifact"](project_id, artifact_hash),
        )
        return DeleteProjectArtifactResponseDTO.model_validate(response)

    async def delete_project(self, project_id: UUID) -> DeleteProjectResponseDTO:
        """Delete a project from the object storage.

        Args:
            project_id: The ID of the project.

        Returns:
            The response from the object storage.
        """
        response = await self._request(
            "DELETE", self.ENDPOINTS["delete_project"](project_id)
        )
        return DeleteProjectResponseDTO.model_validate(response)

    async def upload_experiment_artifact(
        self, experiment_id: UUID, file: UploadFile
    ) -> UploadExperimentArtifactResponseDTO:
        """Upload an experiment artifact to the object storage.

        Args:
            experiment_id: The ID of the experiment.
            file: The upload file.
        """
        file.file.seek(0)
        files = {
            "file": (
                file.filename,
                file.file,
                file.content_type or "application/octet-stream",
            )
        }
        response = await self._request(
            "POST",
            self.ENDPOINTS["upload_experiment_artifact"](experiment_id),
            files=files,
            timeout=None,
        )
        return UploadExperimentArtifactResponseDTO.model_validate(response)

    async def download_experiment_artifact(
        self, experiment_id: UUID, path: str
    ) -> httpx.Response:
        """Download an experiment artifact from the object storage.

        Args:
            experiment_id: The ID of the experiment.
            path: The path of the experiment artifact.

        Returns:
            The response from the object storage.
        """
        response = await self._request(
            "GET",
            self.ENDPOINTS["download_experiment_artifact"](experiment_id, path),
            return_response=True,
        )
        return cast(httpx.Response, response)

    async def delete_experiment_artifact(
        self, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO:
        """Delete an experiment artifact from the object storage.

        Args:
            experiment_id: The ID of the experiment.
            path: The path of the experiment artifact.

        Returns:
            The response from the object storage.
        """
        response = await self._request(
            "DELETE",
            self.ENDPOINTS["delete_experiment_artifact"](experiment_id, path),
        )
        return DeleteExperimentArtifactResponseDTO.model_validate(response)

    async def delete_experiment_artifacts(
        self, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        response = await self._request(
            "DELETE",
            self.ENDPOINTS["delete_experiment_artifacts"](experiment_id),
        )
        return DeleteExperimentArtifactsResponseDTO.model_validate(response)

    async def _request(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any] | list[str] | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, tuple[str | None, Any, str]] | None = None,
        timeout: float | None = 30.0,
        return_response: bool = False,
        return_bytes: bool = False,
    ) -> dict[str, Any] | httpx.Response | bytes:
        """Make a request to the object storage.

        Args:
            method: The HTTP method.
            path: The path of the request.
            json_payload: The JSON payload.
            params: The parameters of the request.
            files: The files of the request.
            timeout: The timeout of the request.
            return_response: Whether to return the response.
            return_bytes: Whether to return the bytes.

        Returns:
            The response from the object storage.
        """
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                json=json_payload,
                params=params,
                files=files,
            )
            response.raise_for_status()
            if return_response:
                return response
            if return_bytes:
                return response.content
            return response.json()
