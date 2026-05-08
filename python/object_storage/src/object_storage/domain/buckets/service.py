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
from .dto import (
    BucketListResultData,
    BucketListRowData,
    BucketObjectStats,
    BucketReconcileResultData,
    UploadBlobResult,
)


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
        """Initialize bucket service with persistence and storage backends.

        Args:
            repository: Bucket registry repository used for metadata operations.
            storage: Storage backend client used for bucket/object operations.
        """

        self._repository = repository
        self._storage = storage

    @property
    def storage(self) -> StorageBackend:
        """Expose storage for sync helpers (e.g. ZIP build in a thread)."""
        return self._storage

    async def get_bucket_name(
        self, project_id: UUID, experiment_id: UUID | None = None
    ) -> str | None:
        """Return the bucket name for a scope when a registry row exists.

        Args:
            project_id: Project UUID used for bucket lookup.
            experiment_id: Optional experiment UUID for experiment-scoped buckets.

        Returns:
            The persisted bucket name, or ``None`` when no row exists for the scope.
        """

        bucket = await self._repository.get_bucket(project_id, experiment_id)
        if bucket is None:
            return None
        return bucket.name

    async def ensure_bucket(
        self, project_id: UUID, experiment_id: UUID | None = None
    ) -> str:
        """Ensure registry row and backing bucket exist for a scope.

        Args:
            project_id: Project UUID used for bucket creation/lookup.
            experiment_id: Optional experiment UUID for experiment-scoped buckets.

        Returns:
            The bucket name for the requested scope.
        """

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
        """Upload one blob and persist bucket size accounting.

        Args:
            project_id: Project UUID identifying the bucket scope.
            experiment_id: Optional experiment UUID for experiment-scoped buckets.
            upload: Incoming upload stream from FastAPI.
            hash: Optional object key override; uses computed SHA-256 when omitted.

        Returns:
            Uploaded object metadata containing byte size and final object hash.

        Raises:
            ValueError: If the bucket scope does not exist.
        """

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
        """Delete one object and decrease stored bucket size when present.

        Args:
            project_id: Project UUID identifying the bucket scope.
            experiment_id: Optional experiment UUID for experiment-scoped buckets.
            hash: Object key/hash to delete.

        Returns:
            ``True`` when the object existed and was deleted, otherwise ``False``.
        """

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
        """Return streaming handle for one object in a scope bucket.

        Args:
            project_id: Project UUID identifying the bucket scope.
            experiment_id: Optional experiment UUID for experiment-scoped buckets.
            hash: Object key/hash to retrieve.

        Returns:
            A streaming binary response object from the storage backend.
        """

        # Match upload paths: ensure registry row + bucket exist (create_all does not repair
        # metadata; downloads must not fail when object storage still has the blob).
        bucket_name = await self.ensure_bucket(project_id, experiment_id)
        await self._repository.commit()
        return self._storage.get_blob(bucket_name, hash)

    async def delete_bucket(
        self, project_id: UUID, experiment_id: UUID | None = None
    ) -> None:
        """Delete one bucket from storage and remove its registry row.

        Args:
            project_id: Project UUID identifying the bucket scope.
            experiment_id: Optional experiment UUID for experiment-scoped buckets.
        """

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
        """Delete every bucket associated with a project.

        Args:
            project_id: Project UUID whose buckets should be removed.
        """

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

    async def list_buckets(
        self,
        project_id: UUID | None = None,
        experiment_id: UUID | None = None,
        reconcile: bool = False,
        *,
        name_contains: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> BucketListResultData:
        """List registry buckets with optional storage stats.

        Args:
            project_id: Optional project filter.
            experiment_id: Optional experiment filter.
            reconcile: When true, also sum object bytes from storage for ``storageSize``.
            name_contains: Optional case-insensitive partial name filter.
            limit: Optional pagination limit.
            offset: Pagination offset.

        Returns:
            Paginated internal result containing typed rows and total count.
        """

        buckets, total = await self._repository.list_buckets(
            project_id,
            experiment_id,
            name_contains=name_contains,
            limit=limit,
            offset=offset,
        )
        rows: list[BucketListRowData] = []
        for bucket in buckets:
            object_count = 0
            storage_size: int | None = None
            if self._storage.bucket_exists(bucket.name):
                entries = self._storage.list_blob_entries(bucket.name)
                object_count = len(entries)
                if reconcile:
                    storage_size = sum(e.size for e in entries)
            rows.append(
                BucketListRowData(
                    id=str(bucket.id),
                    project_id=str(bucket.project_id),
                    experiment_id=(
                        str(bucket.experiment_id) if bucket.experiment_id else None
                    ),
                    name=bucket.name,
                    size=bucket.size,
                    storage_size=storage_size,
                    object_count=object_count,
                    created_at=bucket.created_at.isoformat(),
                    registered=True,
                )
            )
        return BucketListResultData(rows=rows, total=total)

    def _bucket_object_stats(
        self, bucket_name: str, *, sum_object_sizes: bool
    ) -> BucketObjectStats:
        """Single list pass for object count and bytes in storage.

        When ``sum_object_sizes`` is false, bytes are not summed (returns 0).
        """

        if not self._storage.bucket_exists(bucket_name):
            return BucketObjectStats(object_count=0, storage_bytes=0)
        entries = self._storage.list_blob_entries(bucket_name)
        n = len(entries)
        if not sum_object_sizes or n == 0:
            return BucketObjectStats(object_count=n, storage_bytes=0)
        return BucketObjectStats(
            object_count=n,
            storage_bytes=sum(e.size for e in entries),
        )

    def _uuid_fragment_in_name(self, bucket_name: str, uid: UUID) -> bool:
        """Return whether compact UUID appears in a bucket name fragment."""

        compact = str(uid).replace("-", "").lower()
        hay = bucket_name.replace("-", "").lower()
        return compact in hay

    async def list_buckets_merged(
        self,
        project_id: UUID | None = None,
        experiment_id: UUID | None = None,
        reconcile: bool = False,
        *,
        name_contains: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> BucketListResultData:
        """Admin: list buckets from object storage, joined with registry rows when present."""

        storage_names = sorted(self._storage.list_bucket_names())
        reg_by_name = {b.name: b for b in await self._repository.list_all_buckets()}
        needle = (
            name_contains.strip().lower()
            if name_contains and name_contains.strip()
            else None
        )
        filtered: list[tuple[str, Bucket | None]] = []
        for name in storage_names:
            reg = reg_by_name.get(name)
            if needle is not None and needle not in name.lower():
                continue
            if project_id is not None:
                if reg is not None:
                    if reg.project_id != project_id:
                        continue
                elif not self._uuid_fragment_in_name(name, project_id):
                    continue
            if experiment_id is not None:
                if reg is not None:
                    if reg.experiment_id != experiment_id:
                        continue
                elif not self._uuid_fragment_in_name(name, experiment_id):
                    continue
            filtered.append((name, reg))

        total = len(filtered)
        page_pairs = filtered[offset : offset + limit]

        merged: list[BucketListRowData] = []
        for name, reg in page_pairs:
            if reg is not None:
                stats = self._bucket_object_stats(name, sum_object_sizes=reconcile)
                storage_size: int | None = stats.storage_bytes if reconcile else None
                merged.append(
                    BucketListRowData(
                        id=str(reg.id),
                        project_id=str(reg.project_id),
                        experiment_id=(
                            str(reg.experiment_id) if reg.experiment_id else None
                        ),
                        name=name,
                        size=reg.size,
                        storage_size=storage_size,
                        object_count=stats.object_count,
                        created_at=reg.created_at.isoformat(),
                        registered=True,
                    )
                )
            else:
                stats = self._bucket_object_stats(name, sum_object_sizes=True)
                merged.append(
                    BucketListRowData(
                        id=None,
                        project_id=None,
                        experiment_id=None,
                        name=name,
                        size=stats.storage_bytes,
                        storage_size=None,
                        object_count=stats.object_count,
                        created_at=None,
                        registered=False,
                    )
                )
        return BucketListResultData(rows=merged, total=total)

    async def delete_storage_only_bucket(self, name: str) -> bool:
        """Remove an object-store bucket that has no registry row (orphan)."""

        reg = await self._repository.get_bucket_by_name(name)
        if reg is not None:
            return False
        if not self._storage.bucket_exists(name):
            return False
        keys = self._storage.list_blobs(name)
        if keys:
            self._storage.delete_blobs(name, keys)
        self._storage.delete_bucket(name)
        return True

    async def empty_bucket_storage_reset_size(self, bucket_id: UUID) -> Bucket | None:
        """Delete all objects in the backing bucket and set registry ``size`` to 0.

        Keeps the bucket name and registry row so uploads can resume.
        """

        bucket = await self._repository.get_bucket_by_id(bucket_id)
        if bucket is None:
            return None
        if self._storage.bucket_exists(bucket.name):
            keys = self._storage.list_blobs(bucket.name)
            if keys:
                self._storage.delete_blobs(bucket.name, keys)
        await self._repository.update_bucket(
            bucket.project_id, bucket.experiment_id, size=0
        )
        await self._repository.flush()
        return bucket

    async def empty_orphan_bucket_storage(self, name: str) -> bool:
        """Remove all objects from storage when no ``Bucket`` row exists (admin orphan)."""

        trimmed = name.strip()
        if not trimmed:
            return False
        reg = await self._repository.get_bucket_by_name(trimmed)
        if reg is not None:
            return False
        if not self._storage.bucket_exists(trimmed):
            return False
        keys = self._storage.list_blobs(trimmed)
        if keys:
            self._storage.delete_blobs(trimmed, keys)
        return True

    async def delete_bucket_by_id(self, bucket_id: UUID) -> bool:
        """Delete a registered bucket by its UUID identifier.

        Args:
            bucket_id: Registry bucket UUID.

        Returns:
            ``True`` when the bucket row existed and was deleted, else ``False``.
        """

        bucket = await self._repository.get_bucket_by_id(bucket_id)
        if bucket is None:
            return False
        if self._storage.bucket_exists(bucket.name):
            keys = self._storage.list_blobs(bucket.name)
            if keys:
                self._storage.delete_blobs(bucket.name, keys)
            self._storage.delete_bucket(bucket.name)
        await self._repository.delete_bucket_by_id(bucket_id)
        await self._repository.flush()
        return True

    async def reconcile_bucket_by_id(self, bucket_id: UUID) -> BucketReconcileResultData:
        """Recompute and persist one registry bucket size from object storage.

        Args:
            bucket_id: Registry bucket UUID.

        Returns:
            Reconciliation result indicating whether bucket was found, and the
            recalculated size/object totals.
        """

        bucket = await self._repository.get_bucket_by_id(bucket_id)
        if bucket is None:
            return BucketReconcileResultData(found=False, size=0, object_count=0)
        entries = (
            self._storage.list_blob_entries(bucket.name)
            if self._storage.bucket_exists(bucket.name)
            else []
        )
        size = sum(e.size for e in entries)
        await self._repository.update_bucket(
            bucket.project_id, bucket.experiment_id, size=size
        )
        await self._repository.flush()
        return BucketReconcileResultData(
            found=True,
            size=size,
            object_count=len(entries),
        )

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
        """Commit pending bucket metadata changes."""

        await self._repository.commit()

    async def rollback(self) -> None:
        """Rollback pending bucket metadata changes."""

        await self._repository.rollback()
