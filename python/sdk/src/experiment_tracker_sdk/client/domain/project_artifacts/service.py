from __future__ import annotations

from uuid import UUID

from ...request_types import ApiRequestSpec, FileDownloadResponse, FileUploadSpec
from .dto import (
    CheckProjectArtifactsRequest,
    CheckProjectArtifactsResponse,
    DeleteProjectArtifactResponse,
    DeleteProjectResponse,
    SnapshotCreateRequest,
    SnapshotCreateResponse,
    SnapshotFileEntry,
    UploadProjectArtifactResponse,
)


class ProjectArtifactsRequestSpecFactory:
    """Build SDK request specifications for project artifact endpoints.

    Args:
        None. The factory is stateless and uses ``BASE_ENDPOINT`` for route
        construction.

    Result:
        Request-spec builder for project CAS checks, uploads, downloads,
        snapshots, deletes, and cleanup operations.
    """

    BASE_ENDPOINT = "/project-artifacts"

    def check_project_artifacts(
        self, project_id: str | UUID, hashes: list[str]
    ) -> ApiRequestSpec[CheckProjectArtifactsResponse]:
        """Build a request to check which project artifact hashes are missing.

        Args:
            project_id: Project UUID or string identifier.
            hashes: Content hashes to check in project storage.

        Returns:
            ``ApiRequestSpec`` for the project artifact check endpoint.
        """
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}/check"
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=CheckProjectArtifactsRequest(hashes),
            response_model=CheckProjectArtifactsResponse,
        )

    def upload_project_artifact(
        self,
        project_id: str | UUID,
        artifact_hash: str,
        file: FileUploadSpec,
    ) -> ApiRequestSpec[UploadProjectArtifactResponse]:
        """Build a multipart request to upload one project artifact blob.

        Args:
            project_id: Project UUID or string identifier.
            artifact_hash: Expected content hash used as the CAS key.
            file: Multipart file specification containing bytes or a stream.

        Returns:
            ``ApiRequestSpec`` for the project artifact upload endpoint.
        """
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}/upload"
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            query_params={"hash": artifact_hash},
            files={"file": file},
            response_model=UploadProjectArtifactResponse,
        )

    def download_project_artifact(
        self, project_id: str | UUID, artifact_hash: str
    ) -> ApiRequestSpec[FileDownloadResponse]:
        """Build a request to download one project artifact blob.

        Args:
            project_id: Project UUID or string identifier.
            artifact_hash: Content hash identifying the stored artifact.

        Returns:
            ``ApiRequestSpec`` whose response model contains artifact bytes and
            response headers.
        """
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}/artifacts/{artifact_hash}"
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=FileDownloadResponse,
        )

    def create_project_snapshot(
        self,
        project_id: str | UUID,
        experiment_id: str | UUID,
        files: list[SnapshotFileEntry],
    ) -> ApiRequestSpec[SnapshotCreateResponse]:
        """Build a request to create a ZIP snapshot from project artifacts.

        Args:
            project_id: Project UUID or string identifier.
            experiment_id: Experiment UUID or string identifier represented by
                the snapshot.
            files: Manifest entries mapping archive paths to artifact hashes.

        Returns:
            ``ApiRequestSpec`` for the object-storage snapshot creation route.
        """
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}/snapshots"
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=SnapshotCreateRequest(
                project_id=str(project_id),
                experiment_id=str(experiment_id),
                files=files,
            ),
            response_model=SnapshotCreateResponse,
        )

    def download_project_snapshot(
        self, project_id: str | UUID, snapshot_id: str | UUID
    ) -> ApiRequestSpec[FileDownloadResponse]:
        """Build a request to download a project snapshot ZIP archive.

        Args:
            project_id: Project UUID or string identifier that owns the archive.
            snapshot_id: Snapshot UUID or string identifier to download.

        Returns:
            ``ApiRequestSpec`` whose response model contains downloaded bytes
            and response headers.
        """
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        if isinstance(snapshot_id, UUID):
            snapshot_id = str(snapshot_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}/snapshots/{snapshot_id}/download"
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=FileDownloadResponse,
        )

    def delete_project_artifact(
        self, project_id: str | UUID, artifact_hash: str
    ) -> ApiRequestSpec[DeleteProjectArtifactResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}/artifacts/{artifact_hash}"
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=DeleteProjectArtifactResponse,
        )

    def delete_project(
        self, project_id: str | UUID
    ) -> ApiRequestSpec[DeleteProjectResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}"
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=DeleteProjectResponse,
        )


ProjectArtifactsService = ProjectArtifactsRequestSpecFactory
