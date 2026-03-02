from __future__ import annotations

from typing import Protocol
from uuid import UUID

import httpx
from fastapi import UploadFile

from .dto import (
    CheckProjectArtifactsResponseDTO,
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectResponseDTO,
    SnapshotCreateResponseDTO,
    UploadExperimentArtifactResponseDTO,
    UploadProjectArtifactResponseDTO,
)


class ObjectStorageClientProtocol(Protocol):
    async def check_project_artifacts(
        self, project_id: UUID, hashes: list[str]
    ) -> CheckProjectArtifactsResponseDTO: ...

    async def upload_project_artifact(
        self, project_id: UUID, artifact_hash: str, upload: UploadFile
    ) -> UploadProjectArtifactResponseDTO: ...

    async def download_project_artifact(
        self, project_id: UUID, artifact_hash: str
    ) -> bytes: ...

    async def create_project_snapshot(
        self, project_id: UUID, payload: dict
    ) -> SnapshotCreateResponseDTO: ...

    async def download_project_snapshot(
        self, project_id: UUID, snapshot_id: UUID
    ) -> httpx.Response: ...

    async def delete_project_artifact(
        self, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO: ...

    async def delete_project(self, project_id: UUID) -> DeleteProjectResponseDTO: ...

    async def upload_experiment_artifact(
        self, experiment_id: UUID, file: UploadFile
    ) -> UploadExperimentArtifactResponseDTO: ...

    async def download_experiment_artifact(
        self, experiment_id: UUID, path: str
    ) -> httpx.Response: ...

    async def delete_experiment_artifact(
        self, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO: ...

    async def delete_experiment_artifacts(
        self, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO: ...

