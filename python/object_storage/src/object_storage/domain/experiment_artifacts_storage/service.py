"""Business logic for experiment-scoped artifacts storage."""

from __future__ import annotations

import tempfile
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from . import mapper
from .dto import (
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    UploadArtifactResponseDTO,
)
from object_storage.storage import StorageBackend


class ArtifactsStorageService:
    """Store and manage non-deduplicated artifacts per experiment."""

    MAX_SPOOL_SIZE = 10 * 1024 * 1024
    MAX_CHUNK_SIZE = 1024 * 1024

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage

    def _get_experiment_bucket_name(self, experiment_id: UUID) -> str:
        """Get the bucket name for an experiment."""
        return f"experiment-{str(experiment_id)}"

    async def upload_artifact(
        self, experiment_id: UUID, upload: UploadFile
    ) -> UploadArtifactResponseDTO:
        """Upload one artifact under an experiment-specific prefix."""
        bucket_name = self._get_experiment_bucket_name(experiment_id)
        artifact_path = uuid4().hex
        self._storage.ensure_bucket(bucket_name)
        spool: tempfile.SpooledTemporaryFile | None = None
        try:
            spool, size = await self._spool_upload(upload)
            self._storage.put_blob(bucket_name, artifact_path, spool, size)
            return mapper.upload_to_response(path=artifact_path, size=size)
        finally:
            if spool is not None:
                spool.close()

    async def get_artifact_stream(self, experiment_id: UUID, artifact_path: str):
        """Get a streaming handle for one artifact."""

        bucket_name = self._get_experiment_bucket_name(experiment_id)
        self._storage.ensure_bucket(bucket_name)
        return self._storage.get_blob(bucket_name, artifact_path)

    async def delete_artifact(
        self, experiment_id: UUID, artifact_path: str
    ) -> DeleteArtifactResponseDTO:
        """Delete one artifact for an experiment."""

        bucket_name = self._get_experiment_bucket_name(experiment_id)
        deleted = self._storage.delete_blob(bucket_name, artifact_path)
        return mapper.delete_artifact_to_response(deleted)

    async def delete_experiment(
        self, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        """Delete all artifacts that belong to an experiment."""

        bucket_name = self._get_experiment_bucket_name(experiment_id)
        deleted_count = self._storage.delete_bucket(bucket_name)
        return mapper.delete_experiment_to_response(deleted_count)

    async def _spool_upload(
        self, upload: UploadFile
    ) -> tuple[tempfile.SpooledTemporaryFile, int]:
        """Stream upload into a spooled temp file and return byte size."""

        size = 0
        spool = tempfile.SpooledTemporaryFile(max_size=self.MAX_SPOOL_SIZE)
        while True:
            chunk = await upload.read(self.MAX_CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            spool.write(chunk)
        spool.seek(0)
        return spool, size
