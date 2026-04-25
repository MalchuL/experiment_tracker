"""HTTP client for object storage service (project-artifacts, experiment-artifacts)."""

from __future__ import annotations

import json
from typing import Any, Protocol, cast
from uuid import UUID

import httpx
from fastapi import UploadFile

from .dto import (
    CheckProjectArtifactsResponseDTO,
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectResponseDTO,
    ExperimentTrackedArtifactListDTO,
    ExperimentTrackedArtifactItemDTO,
    ExperimentTrackedArtifactInfoDTO,
    ExperimentTrackedUploadResponseDTO,
    ExperimentUntrackedUploadResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadProjectArtifactResponseDTO,
)


class TransferStrategyProtocol(Protocol):
    async def upload_file(
        self,
        base_url: str,
        path: str,
        upload: UploadFile,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]: ...

    async def download_bytes(
        self,
        base_url: str,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> bytes: ...

    async def download_response(
        self,
        base_url: str,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response: ...


class HttpxTransferStrategy:
    """Reusable upload/download transport used by object-storage endpoints."""

    async def upload_file(
        self,
        base_url: str,
        path: str,
        upload: UploadFile,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        upload.file.seek(0)
        files = {
            "file": (
                upload.filename,
                upload.file,
                upload.content_type or "application/octet-stream",
            )
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method="POST",
                url=f"{base_url}{path}",
                params=params,
                files=files,
            )
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

    async def download_bytes(
        self,
        base_url: str,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method="GET",
                url=f"{base_url}{path}",
                params=params,
            )
            response.raise_for_status()
            return response.content

    async def download_response(
        self,
        base_url: str,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method="GET",
                url=f"{base_url}{path}",
                params=params,
            )
            response.raise_for_status()
            return response


class ObjectStorageClient:
    """HTTP client for object storage service (project-artifacts, experiment-artifacts).

    This client is used to check, upload, download, create snapshots, delete project and experiment artifacts.

    Args:
        base_url: The base URL of the object storage service.
    """

    ENDPOINTS: dict[str, Any] = {
        "check_project_artifacts": lambda project_id: f"/project-artifacts/{project_id}/check",
        "upload_project_artifact": lambda project_id: f"/project-artifacts/{project_id}/upload",
        "download_project_artifact": lambda project_id, artifact_hash: f"/project-artifacts/{project_id}/artifacts/{artifact_hash}",
        "create_project_snapshot": lambda project_id: f"/project-artifacts/{project_id}/snapshots",
        "download_project_snapshot": lambda project_id, snapshot_id: f"/project-artifacts/{project_id}/snapshots/{snapshot_id}/download",
        "delete_project_artifact": lambda project_id, artifact_hash: f"/project-artifacts/{project_id}/artifacts/{artifact_hash}",
        "delete_project": lambda project_id: f"/project-artifacts/{project_id}",
        "upload_experiment_untracked": lambda pid, eid: (
            f"/experiment-artifacts/projects/{pid}/experiments/{eid}/upload-untracked"
        ),
        "upload_experiment_tracked": lambda pid, eid: (
            f"/experiment-artifacts/projects/{pid}/experiments/{eid}/upload-tracked"
        ),
        "list_experiment_tracked": lambda pid, eid: (
            f"/experiment-artifacts/projects/{pid}/experiments/{eid}/artifacts"
        ),
        "get_experiment_tracked_info": lambda pid, eid: (
            f"/experiment-artifacts/projects/{pid}/experiments/{eid}/artifacts/info"
        ),
        "download_experiment_artifact": lambda pid, eid, h: (
            f"/experiment-artifacts/projects/{pid}/experiments/{eid}/artifacts/{h}"
        ),
        "delete_experiment_artifact": lambda pid, eid, h: (
            f"/experiment-artifacts/projects/{pid}/experiments/{eid}/artifacts/{h}"
        ),
        "delete_all_experiment_artifacts": lambda pid, eid: (
            f"/experiment-artifacts/projects/{pid}/experiments/{eid}"
        ),
    }

    def __init__(
        self,
        base_url: str,
        transfer_strategy: TransferStrategyProtocol | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._transfer_strategy: TransferStrategyProtocol = (
            transfer_strategy or HttpxTransferStrategy()
        )

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
        response = await self._transfer_strategy.upload_file(
            base_url=self.base_url,
            path=self.ENDPOINTS["upload_project_artifact"](project_id),
            upload=upload,
            params={"artifact_hash": artifact_hash},
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
        response = await self._transfer_strategy.download_bytes(
            base_url=self.base_url,
            path=self.ENDPOINTS["download_project_artifact"](project_id, artifact_hash),
            timeout=None,
        )
        return response

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

    async def upload_experiment_untracked(
        self,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        artifact_hash: str | None = None,
    ) -> ExperimentUntrackedUploadResponseDTO:
        params: dict[str, Any] | None = (
            {"artifact_hash": artifact_hash} if artifact_hash else None
        )
        response = await self._transfer_strategy.upload_file(
            base_url=self.base_url,
            path=self.ENDPOINTS["upload_experiment_untracked"](
                project_id, experiment_id
            ),
            upload=file,
            params=params,
            timeout=None,
        )
        return ExperimentUntrackedUploadResponseDTO.model_validate(response)

    async def upload_experiment_tracked(
        self,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        artifact_hash: str | None = None,
        file_path: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperimentTrackedUploadResponseDTO:
        params: dict[str, Any] = {}
        if content_type is not None:
            params["content_type"] = content_type
        if artifact_hash is not None:
            params["artifact_hash"] = artifact_hash
        if file_path is not None:
            params["file_path"] = file_path
        if metadata is not None:
            params["metadata"] = json.dumps(metadata)
        response = await self._transfer_strategy.upload_file(
            base_url=self.base_url,
            path=self.ENDPOINTS["upload_experiment_tracked"](project_id, experiment_id),
            upload=file,
            params=params,
            timeout=None,
        )
        return ExperimentTrackedUploadResponseDTO.model_validate(response)

    async def list_experiment_tracked_artifacts(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        file_paths: list[str] | None = None,
    ) -> ExperimentTrackedArtifactListDTO:
        path = self.ENDPOINTS["list_experiment_tracked"](project_id, experiment_id)
        url = f"{self.base_url}{path}"
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if file_paths:
            params["file_path"] = file_paths
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                "GET",
                url,
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
        return ExperimentTrackedArtifactListDTO.model_validate(payload)

    async def get_experiment_tracked_artifact_info(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        file_path: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentTrackedArtifactInfoDTO:
        params: dict[str, Any] = {}
        if file_path is not None:
            params["file_path"] = file_path
        if blob_id is not None:
            params["blob_id"] = str(blob_id)
        if artifact_hash is not None:
            params["artifact_hash"] = artifact_hash
        response = await self._request(
            "GET",
            self.ENDPOINTS["get_experiment_tracked_info"](project_id, experiment_id),
            params=params,
        )
        return ExperimentTrackedArtifactInfoDTO.model_validate(response)

    async def download_experiment_artifact(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_hash: str,
        *,
        tracked: bool = False,
    ) -> httpx.Response:
        response = await self._transfer_strategy.download_response(
            base_url=self.base_url,
            path=self.ENDPOINTS["download_experiment_artifact"](
                project_id, experiment_id, artifact_hash
            ),
            params={"tracked": "true" if tracked else "false"},
        )
        return response

    async def delete_experiment_artifact(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_hash: str,
    ) -> DeleteExperimentArtifactResponseDTO:
        response = await self._request(
            "DELETE",
            self.ENDPOINTS["delete_experiment_artifact"](
                project_id, experiment_id, artifact_hash
            ),
        )
        return DeleteExperimentArtifactResponseDTO.model_validate(response)

    async def delete_all_experiment_artifacts(
        self, project_id: UUID, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        response = await self._request(
            "DELETE",
            self.ENDPOINTS["delete_all_experiment_artifacts"](
                project_id, experiment_id
            ),
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
