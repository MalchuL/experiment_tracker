"""Central bucket naming and object-storage bucket lifecycle.

Naming matches ``ObjectStorageService`` (project CAS) and ``ArtifactsStorageService``
(experiment artifacts). Callers can use :class:`BucketOperationsService` for storage-only
operations and :class:`BucketRegistryService` when persisting :class:`~object_storage.db.models.Bucket` rows.
"""

from __future__ import annotations

import tempfile
from typing import BinaryIO, cast
from uuid import UUID

from fastapi import UploadFile

from object_storage.domain.buckets.repository import BucketsRepository
from object_storage.db.models import Bucket
from object_storage.storage import StorageBackend
from object_storage.logger import logger
from experiment_tracker_shared import create_sha256_hasher
from .dto import UploadBlobResult


def project_experiment_bucket_name(
    project_id: UUID, experiment_id: UUID | None = None
) -> str:
    """Object storage name for a registered (project, experiment) pair.

    Keep names short enough for S3/MinIO bucket constraints (max 63 chars).
    """

    if experiment_id is None:
        return f"project-{str(project_id)}"
    return f"prj-{project_id.hex[:16]}-exp-{experiment_id.hex[:16]}"


class BucketRegistryService:
    """Create ``Bucket`` metadata rows and the corresponding object-storage bucket."""

    MAX_SPOOL_SIZE = 10 * 1024 * 1024
    MAX_CHUNK_SIZE = 1024 * 1024

    def __init__(self, repository: BucketsRepository, storage: StorageBackend) -> None:
        self._repository = repository
        self._storage = storage

    @property
    def storage(self) -> StorageBackend:
        """Expose storage for sync helpers (e.g. ZIP build in a thread)."""
        return self._storage

    async def get_bucket_name(
        self, project_id: UUID, experiment_id: UUID | None = None
    ) -> str | None:
        bucket = await self._repository.get_bucket(project_id, experiment_id)
        if bucket is None:
            return None
        return bucket.name

    async def ensure_bucket(
        self, project_id: UUID, experiment_id: UUID | None = None
    ) -> str:
        bucket = await self._repository.get_bucket(project_id, experiment_id)
        if bucket is None:
            bucket = Bucket(
                project_id=project_id,
                experiment_id=experiment_id,
                name=project_experiment_bucket_name(project_id, experiment_id),
            )
            await self._repository.create_bucket(bucket)
            await self._repository.flush()
            self._storage.ensure_bucket(bucket.name)
        return bucket.name

    # TODO Make more optimal because it uses the whole upload in memory
    async def upload_blob(
        self,
        project_id: UUID,
        experiment_id: UUID | None,
        upload: UploadFile,
        hash: str | None = None,
    ) -> UploadBlobResult:
        bucket_name = await self.get_bucket_name(project_id, experiment_id)
        if bucket_name is None:
            raise ValueError(f"Bucket {project_id} {experiment_id} not found")
        spool: tempfile.SpooledTemporaryFile | None = None
        try:
            spool, size, computed_hash = await self._spool_upload(upload)
            final_hash = hash or computed_hash
            self._storage.put_blob(
                bucket_name,
                final_hash,
                cast(BinaryIO, spool),
                size,
            )
            await self._repository.increment_bucket_size(
                project_id, experiment_id, size
            )
            await self._repository.flush()
            return UploadBlobResult(size=size, hash=final_hash)
        finally:
            if spool is not None:
                spool.close()

    async def upload_blob_verifying_sha256(
        self,
        project_id: UUID,
        experiment_id: UUID | None,
        upload: UploadFile,
        expected_sha256_hex: str,
    ) -> UploadBlobResult:
        """Spool the upload, verify SHA-256 matches ``expected_sha256_hex``, store under that key.

        Comparison is case-insensitive. The object key uses the lowercase form of
        ``expected_sha256_hex``. Raises :class:`ValueError` with a ``Hash mismatch`` message
        if the content digest differs.
        """

        bucket_name = await self.get_bucket_name(project_id, experiment_id)
        if bucket_name is None:
            raise ValueError(f"Bucket {project_id} {experiment_id} not found")
        expected = expected_sha256_hex.strip().lower()
        spool: tempfile.SpooledTemporaryFile | None = None
        try:
            spool, size, computed_hash = await self._spool_upload(upload)
            if computed_hash.lower() != expected:
                raise ValueError(
                    f"Hash mismatch, computed: {computed_hash}, expected: {expected_sha256_hex}"
                )
            self._storage.put_blob(
                bucket_name,
                expected,
                cast(BinaryIO, spool),
                size,
            )
            await self._repository.increment_bucket_size(
                project_id, experiment_id, size
            )
            await self._repository.flush()
            return UploadBlobResult(size=size, hash=expected)
        finally:
            if spool is not None:
                spool.close()

    async def delete_blob(
        self,
        project_id: UUID,
        experiment_id: UUID | None,
        hash: str,
    ) -> bool:
        bucket_name = await self.get_bucket_name(project_id, experiment_id)
        if bucket_name is None:
            return False
        if not self._storage.exists_blob(bucket_name, hash):
            return False
        size = self._storage.size_blob(bucket_name, hash)
        await self._repository.decrement_bucket_size(project_id, experiment_id, size)
        self._storage.delete_blob(bucket_name, hash)
        await self._repository.flush()
        return True

    async def get_blob_stream(
        self, project_id: UUID, experiment_id: UUID | None, hash: str
    ) -> BinaryIO:
        bucket_name = await self.get_bucket_name(project_id, experiment_id)
        if bucket_name is None:
            raise ValueError(f"Bucket {project_id} {experiment_id} not found")
        blob_stream = self._storage.get_blob(bucket_name, hash)
        return blob_stream

    async def delete_bucket(
        self, project_id: UUID, experiment_id: UUID | None = None
    ) -> None:
        bucket = await self._repository.get_bucket(project_id, experiment_id)
        if bucket is None:
            return
        bucket_name = bucket.name
        keys = self._storage.list_blobs(bucket_name)
        if keys:
            self._storage.delete_blobs(bucket_name, keys)
        self._storage.delete_bucket(bucket_name)
        await self._repository.delete_bucket(project_id, experiment_id)
        await self._repository.flush()

    async def delete_all_project_buckets(self, project_id: UUID) -> None:
        buckets = await self._repository.get_all_project_buckets(project_id)
        for bucket in buckets:
            exists = self._storage.bucket_exists(bucket.name)
            if exists:
                keys = self._storage.list_blobs(bucket.name)
                if keys:
                    self._storage.delete_blobs(bucket.name, keys)
                self._storage.delete_bucket(bucket.name)
            else:
                logger.warning("Bucket %s does not exist", bucket.name)
        await self._repository.delete_all_project_buckets(project_id)
        await self._repository.flush()

    async def _spool_upload(
        self, upload: UploadFile
    ) -> tuple[tempfile.SpooledTemporaryFile, int, str]:
        """Stream the upload into a spooled file while computing its SHA-256 hash."""

        hasher = create_sha256_hasher()
        size = 0
        spool = tempfile.SpooledTemporaryFile(max_size=self.MAX_SPOOL_SIZE)
        while True:
            chunk = await upload.read(self.MAX_CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            hasher.update(chunk)
            spool.write(chunk)
        spool.seek(0)
        return spool, size, hasher.hexdigest()

    async def commit(self) -> None:
        await self._repository.commit()

    async def rollback(self) -> None:
        await self._repository.rollback()
