from __future__ import annotations

from uuid import UUID

from .dto import (
    CheckProjectArtifactsRequest,
    CheckProjectArtifactsResponse,
    DeleteProjectArtifactResponse,
    DeleteProjectResponse,
    UploadProjectArtifactResponse,
)
from ...request import ApiRequestSpec, FileUploadSpec


class ProjectArtifactsRequestSpecFactory:
    BASE_ENDPOINT = "/project-artifacts"

    def check_project_artifacts(
        self, project_id: str | UUID, hashes: list[str]
    ) -> ApiRequestSpec[CheckProjectArtifactsResponse]:
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
    ) -> ApiRequestSpec:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}/artifacts/{artifact_hash}"
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_is_binary=True,
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

    def delete_project(self, project_id: str | UUID) -> ApiRequestSpec[DeleteProjectResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = f"{self.BASE_ENDPOINT}/{project_id}"
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=DeleteProjectResponse,
        )


ProjectArtifactsService = ProjectArtifactsRequestSpecFactory
