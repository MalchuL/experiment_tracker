"""Business logic for CAS blob storage and snapshot creation."""

from __future__ import annotations

import re
import tempfile
import zipfile
from pathlib import PurePosixPath
from typing import Any, BinaryIO
from uuid import UUID

import anyio
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from .mapper import ProjectArtifactsStorageMapper
from .dto import (
    BucketListResponseDTO,
    ClearStorageBucketResponseDTO,
    DeleteProjectSnapshotResponseDTO,
    DeleteStorageBucketResponseDTO,
    BlobCheckResponseDTO,
    DeleteBlobResponseDTO,
    ExperimentBucketsUsageDTO,
    ProjectArtifactsUsageItemDTO,
    ProjectSnapshotsUsageDTO,
    ProjectUsageResponseDTO,
    ReconcileStorageBucketResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    SnapshotFileEntryDTO,
    SnapshotManifestResponseDTO,
    UploadBlobResponseDTO,
)
from .repository import ObjectStorageRepository
from object_storage.domain.buckets.service import (
    BucketRegistryService,
    project_experiment_bucket_name,
)
from object_storage.domain.experiment_artifacts_storage.repository import (
    ExperimentArtifactsRepository,
)


class ObjectStorageService:
    _SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")
    _INVALID_PATH_CHARS_RE = re.compile(r"[:\x00-\x1f]")

    """CAS workflow service for blob checking, uploads, and snapshots."""

    def __init__(
        self,
        repository: ObjectStorageRepository,
        buckets_service: BucketRegistryService,
        experiment_artifacts_repository: ExperimentArtifactsRepository,
    ) -> None:
        """Initialize with metadata repository and project-scoped bucket registry."""

        self._repository = repository
        self._buckets_service = buckets_service
        self._experiment_artifacts_repository = experiment_artifacts_repository
        self._mapper = ProjectArtifactsStorageMapper()

    async def delete_project(self, project_id: UUID) -> bool:
        """Delete all object-storage records and buckets for a project.

        Args:
            project_id: Project UUID whose blobs, snapshots, and buckets are removed.

        Returns:
            Always ``True`` after the deletion flow completes.
        """

        await self._buckets_service.delete_all_project_buckets(project_id)
        await self._repository.delete_all_blobs(project_id)
        await self._repository.delete_all_snapshots(project_id)
        await self._repository.commit()
        return True

    async def cleanup_project_cas_only(self, project_id: UUID) -> bool:
        """Remove project CAS metadata and blob objects; keep snapshots and experiment buckets."""

        hashes = await self._repository.list_project_blob_hashes(project_id)
        await self._repository.delete_all_blobs(project_id)
        for h in hashes:
            await self._buckets_service.delete_blob(project_id, None, h)
        await self._repository.commit()
        return True

    async def cleanup_project_snapshots_only(self, project_id: UUID) -> bool:
        """Remove all project snapshots and unreferenced CAS blobs; keep other data."""

        ids = await self._repository.list_snapshot_ids_for_project(project_id)
        for sid in ids:
            await self.delete_project_snapshot(project_id, sid)
        return True

    async def cleanup_project_experiment_buckets_only(self, project_id: UUID) -> bool:
        """Remove experiment-scoped buckets and tracked experiment blobs; keep project CAS."""

        bucket_result = await self._buckets_service.list_buckets(
            project_id=project_id,
            limit=None,
            offset=0,
        )
        for row in bucket_result.rows:
            if row.experiment_id is None:
                continue
            eid = UUID(row.experiment_id)
            await self._experiment_artifacts_repository.delete_all_experiment_blobs(
                project_id, eid
            )
            await self._buckets_service.delete_bucket(project_id, eid)
        await self._repository.commit()
        return True

    async def check_project_blobs(
        self, project_id: UUID, hashes: list[str]
    ) -> BlobCheckResponseDTO:
        """Return which requested hashes are missing from project CAS metadata.

        Args:
            project_id: Project UUID used for blob lookup.
            hashes: Candidate blob hashes to validate.

        Returns:
            A DTO listing normalized hashes that are absent in metadata storage.
        """

        await self._buckets_service.ensure_bucket(project_id, None)
        if not hashes:
            return self._mapper.missing_hashes_to_response([])
        normalized_hashes = [self._normalize_hash(blob_hash) for blob_hash in hashes]
        existing = await self._repository.fetch_existing_blob_hashes(
            project_id, normalized_hashes
        )
        missing = [
            blob_hash for blob_hash in normalized_hashes if blob_hash not in existing
        ]
        return self._mapper.missing_hashes_to_response(missing)

    async def upload_project_blob(
        self, project_id: UUID, blob_hash: str, upload: UploadFile
    ) -> UploadBlobResponseDTO:
        """Upload one project-scoped CAS blob after SHA-256 verification.

        Args:
            project_id: Project UUID that owns the CAS bucket.
            blob_hash: Expected SHA-256 hash string (hex).
            upload: Incoming upload stream from FastAPI.

        Returns:
            Upload status DTO (``ok`` or ``exists``).

        Raises:
            HTTPException: If hash validation fails or metadata persistence fails.
        """

        blob_hash = self._normalize_hash(blob_hash)
        existing = await self._repository.fetch_blob(project_id, blob_hash)
        if existing:
            return self._mapper.upload_status_to_response("exists")

        await self._buckets_service.ensure_bucket(project_id, None)
        try:
            upload_result = await self._buckets_service.upload_blob_verifying_sha256(
                project_id, None, upload, blob_hash
            )
        except ValueError as exc:
            detail = str(exc)
            if detail.startswith("Hash mismatch"):
                raise HTTPException(status_code=400, detail=detail)
            raise
        await self._repository.add_blob(
            project_id,
            upload_result.hash,
            upload_result.size,
            upload.content_type or "application/octet-stream",
        )
        try:
            await self._repository.commit()
        except IntegrityError:
            await self._repository.rollback()
            await self._buckets_service.delete_blob(
                project_id, None, upload_result.hash
            )
            raise HTTPException(
                status_code=500, detail="Failed to add blob to repository"
            )
        return self._mapper.upload_status_to_response("ok")

    async def create_project_snapshot(
        self, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        """Create a snapshot manifest that references existing project CAS blobs.

        Args:
            payload: Snapshot creation request with project id and manifest entries.

        Returns:
            DTO containing the created snapshot identifier.

        Raises:
            HTTPException: If any path is invalid or referenced blobs are missing.
        """

        normalized_files = [
            entry.model_copy(
                update={
                    "hash": self._normalize_hash(entry.hash),
                    "path": self._normalize_path(entry.path),
                }
            )
            for entry in payload.files
        ]
        errors = []
        for entry in normalized_files:
            if not self._validate_relative_path(entry.path):
                errors.append(
                    f"Invalid path: {entry.path}. Path must be relative and not contain '..' or start with '/'"
                )
        if errors:
            raise HTTPException(status_code=400, detail="\n".join(errors))
        hashes = [entry.hash for entry in normalized_files]
        if hashes:
            blob_sizes = await self._repository.fetch_blob_sizes(
                payload.project_id, hashes
            )
            missing = [blob_hash for blob_hash in hashes if blob_hash not in blob_sizes]
            if missing:
                raise HTTPException(
                    status_code=400, detail=f"Missing blobs: {', '.join(missing)}"
                )
            size_errors = [
                f"Size mismatch for {entry.path}: expected {blob_sizes[entry.hash]}, got {entry.size}"
                for entry in normalized_files
                if entry.size is not None and entry.size != blob_sizes[entry.hash]
            ]
            if size_errors:
                raise HTTPException(status_code=400, detail="\n".join(size_errors))
            normalized_files = [
                entry.model_copy(update={"size": blob_sizes[entry.hash]})
                for entry in normalized_files
            ]

        manifest = self._mapper.snapshot_files_to_manifest(normalized_files)
        snapshot = await self._repository.create_snapshot(payload.project_id, manifest)
        if hashes:
            await self._repository.increment_blob_ref_counts(payload.project_id, hashes)
        await self._repository.commit()
        await self._repository.refresh(snapshot)
        return self._mapper.snapshot_id_to_response(snapshot.id)

    async def delete_project_snapshot(
        self, project_id: UUID, snapshot_id: UUID
    ) -> DeleteProjectSnapshotResponseDTO:
        """Delete one snapshot and orphaned blobs referenced only by that snapshot.

        Args:
            project_id: Project UUID owning the snapshot.
            snapshot_id: Snapshot UUID to delete.

        Returns:
            DTO indicating deletion success and hashes of physically removed blobs.

        Raises:
            HTTPException: If snapshot does not exist for the project.
        """

        snapshot = await self._repository.fetch_snapshot(snapshot_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        if snapshot.project_id != project_id:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        snapshot_hashes = [entry["hash"] for entry in snapshot.manifest]
        await self._repository.decrement_blob_ref_counts(project_id, snapshot_hashes)
        deleted_blobs = []
        for hash in snapshot_hashes:
            blob = await self._repository.fetch_blob(project_id, hash)
            if blob is not None and blob.ref_count <= 0:
                await self._buckets_service.delete_blob(project_id, None, hash)
                await self._repository.delete_blob(project_id, hash)
                deleted_blobs.append(hash)
        await self._repository.delete_snapshot(snapshot_id)
        await self._repository.commit()
        return DeleteProjectSnapshotResponseDTO(
            deleted=True,
            deleted_blobs=deleted_blobs,
        )

    async def get_project_snapshot_manifest(
        self, project_id: UUID, snapshot_id: UUID
    ) -> SnapshotManifestResponseDTO:
        """Return snapshot manifest metadata without reading blob contents."""

        snapshot = await self._repository.fetch_snapshot(snapshot_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        if snapshot.project_id != project_id:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        files = [
            SnapshotFileEntryDTO.model_validate(
                {
                    **entry,
                    "hash": self._normalize_hash(str(entry["hash"])),
                }
            )
            for entry in snapshot.manifest
        ]
        return SnapshotManifestResponseDTO(snapshot_id=snapshot.id, files=files)

    async def get_project_usage(self, project_id: UUID) -> ProjectUsageResponseDTO:
        """Return combined project usage across CAS, snapshots, and experiment buckets.

        Args:
            project_id: Project UUID whose usage should be aggregated.

        Returns:
            Typed usage payload with per-category totals and overall byte usage.
        """

        blob_usage = await self._repository.get_project_blob_usage(project_id)
        bucket_result = await self._buckets_service.list_buckets(
            project_id=project_id,
            limit=None,
            offset=0,
        )
        buckets = bucket_result.rows
        experiment_buckets = [
            bucket for bucket in buckets if bucket.experiment_id is not None
        ]
        experiment_bucket_bytes = sum(int(bucket.size) for bucket in experiment_buckets)
        project_bucket = next(
            (bucket for bucket in buckets if bucket.experiment_id is None),
            None,
        )
        total = (
            int(blob_usage["projectArtifacts"]["bytes"])
            + experiment_bucket_bytes
        )
        return ProjectUsageResponseDTO(
            project_id=str(project_id),
            project_artifacts=ProjectArtifactsUsageItemDTO(
                count=int(blob_usage["projectArtifacts"]["count"]),
                bytes=int(blob_usage["projectArtifacts"]["bytes"]),
            ),
            snapshots=ProjectSnapshotsUsageDTO(
                count=int(blob_usage["snapshots"]["count"]),
                referenced_blob_count=int(blob_usage["snapshots"]["referencedBlobCount"]),
                bytes=int(blob_usage["snapshots"]["bytes"]),
            ),
            experiment_buckets=ExperimentBucketsUsageDTO(
                count=len(experiment_buckets),
                bytes=experiment_bucket_bytes,
            ),
            project_bucket=(
                self._mapper.bucket_row_data_to_response(project_bucket)
                if project_bucket is not None
                else None
            ),
            total_bytes=total,
        )

    async def list_buckets(
        self,
        project_id: UUID | None = None,
        experiment_id: UUID | None = None,
        reconcile: bool = False,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> BucketListResponseDTO:
        """List buckets visible to storage admin views.

        Args:
            project_id: Optional project filter.
            experiment_id: Optional experiment filter.
            reconcile: Whether to compute storage-side byte totals.
            q: Optional partial-name filter.
            limit: Maximum number of buckets to return.
            offset: Pagination offset.

        Returns:
            Paginated bucket listing payload.
        """

        bucket_result = await self._buckets_service.list_buckets_merged(
            project_id=project_id,
            experiment_id=experiment_id,
            reconcile=reconcile,
            name_contains=q,
            limit=limit,
            offset=offset,
        )
        return BucketListResponseDTO(
            buckets=[
                self._mapper.bucket_row_data_to_response(row)
                for row in bucket_result.rows
            ],
            total=bucket_result.total,
            limit=limit,
            offset=offset,
        )

    async def delete_storage_only_bucket(
        self, name: str
    ) -> DeleteStorageBucketResponseDTO:
        """Delete orphan bucket from object storage only.

        Args:
            name: Bucket name to delete when not registered in metadata DB.

        Returns:
            DTO indicating whether the bucket was deleted.
        """

        deleted = await self._buckets_service.delete_storage_only_bucket(name.strip())
        return DeleteStorageBucketResponseDTO(deleted=deleted)

    async def delete_bucket(self, bucket_id: UUID) -> DeleteStorageBucketResponseDTO:
        """Delete a registered bucket by id.

        Args:
            bucket_id: Registry bucket UUID.

        Returns:
            DTO indicating whether the bucket existed and was deleted.
        """

        deleted = await self._buckets_service.delete_bucket_by_id(bucket_id)
        await self._repository.commit()
        return DeleteStorageBucketResponseDTO(deleted=deleted)

    async def reconcile_bucket(
        self, bucket_id: UUID
    ) -> ReconcileStorageBucketResponseDTO:
        """Recompute a registered bucket size and object count from storage.

        Args:
            bucket_id: Registry bucket UUID.

        Returns:
            Reconciliation result for the bucket.
        """

        result = await self._buckets_service.reconcile_bucket_by_id(bucket_id)
        await self._repository.commit()
        return ReconcileStorageBucketResponseDTO(
            found=result.found,
            size=result.size,
            object_count=result.object_count,
        )

    async def clear_bucket(self, bucket_id: UUID) -> ClearStorageBucketResponseDTO:
        """Empty one registered bucket and clear associated object-storage metadata.

        Args:
            bucket_id: Registry bucket UUID.

        Returns:
            DTO indicating whether the bucket existed and was cleared.
        """

        bucket = await self._buckets_service.empty_bucket_storage_reset_size(bucket_id)
        if bucket is None:
            return ClearStorageBucketResponseDTO(cleared=False)
        if bucket.experiment_id is None:
            await self._repository.delete_all_snapshots(bucket.project_id)
            await self._repository.delete_all_blobs(bucket.project_id)
        else:
            await self._experiment_artifacts_repository.delete_all_experiment_blobs(
                bucket.project_id, bucket.experiment_id
            )
        await self._repository.commit()
        return ClearStorageBucketResponseDTO(cleared=True)

    async def clear_storage_only_bucket(
        self, name: str
    ) -> ClearStorageBucketResponseDTO:
        """Remove all objects from an orphan bucket while keeping the bucket itself.

        Args:
            name: Storage bucket name expected to have no registry row.

        Returns:
            DTO indicating whether the orphan bucket was cleared.
        """

        cleared = await self._buckets_service.empty_orphan_bucket_storage(name)
        return ClearStorageBucketResponseDTO(cleared=cleared)

    async def prepare_project_snapshot_download(
        self, project_id: UUID, snapshot_id: UUID
    ) -> tuple[str, str]:
        """Build a temporary ZIP archive for a snapshot download response.

        Args:
            project_id: Project UUID owning the snapshot.
            snapshot_id: Snapshot UUID to export.

        Returns:
            A tuple ``(zip_path, filename)`` where ``zip_path`` is a temporary file path.

        Raises:
            HTTPException: If the snapshot does not exist.
        """

        snapshot = await self._repository.fetch_snapshot(snapshot_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        await self._buckets_service.ensure_bucket(project_id, None)
        zip_path = await anyio.to_thread.run_sync(
            self._build_zip,
            self._buckets_service.storage,
            project_id,
            snapshot.manifest,
        )
        filename = f"snapshot-{snapshot_id}.zip"
        return zip_path, filename

    async def get_project_blob_stream(
        self, project_id: UUID, blob_hash: str
    ) -> BinaryIO:
        """Return streaming storage response for a project CAS blob.

        Args:
            project_id: Project UUID owning the blob.
            blob_hash: SHA-256 blob hash.

        Returns:
            Storage backend stream object for iterating blob bytes.

        Raises:
            HTTPException: If blob metadata is missing.
        """

        blob_hash = self._normalize_hash(blob_hash)
        blob = await self._repository.fetch_blob(project_id, blob_hash)
        if blob is None:
            raise HTTPException(status_code=404, detail="Blob not found")
        await self._buckets_service.ensure_bucket(project_id, None)
        return await self._buckets_service.get_blob_stream(
            project_id, None, blob_hash
        )

    async def delete_project_blob(
        self, project_id: UUID, blob_hash: str
    ) -> DeleteBlobResponseDTO:
        """Delete a single CAS blob and its metadata row."""

        blob_hash = self._normalize_hash(blob_hash)
        metadata = await self._repository.fetch_blob(project_id, blob_hash)
        if metadata is not None and metadata.ref_count > 0:
            raise HTTPException(
                status_code=400, detail=f"Blob {blob_hash} is referenced by a snapshot"
            )
        deleted_metadata = await self._repository.delete_blob(project_id, blob_hash)
        deleted_storage = await self._buckets_service.delete_blob(
            project_id, None, blob_hash
        )
        if deleted_metadata or deleted_storage:
            await self._repository.commit()
        return self._mapper.delete_blob_to_response(deleted_metadata or deleted_storage)

    def _normalize_hash(self, blob_hash: str) -> str:
        """Validate SHA-256 hex format and normalize to lowercase."""

        normalized = blob_hash.strip()
        if not self._SHA256_HEX_RE.fullmatch(normalized):
            raise HTTPException(status_code=400, detail="Invalid blob hash format")
        return normalized.lower()

    def _normalize_path(self, path: str) -> str:
        """Normalize the path to a relative path."""

        return path.strip().replace("\\", "/")

    def _validate_relative_path(self, path: str) -> bool:
        """
        Reject unsafe manifest paths.

        Rules:
        - must be relative
        - must not traverse to parent directories
        - must not include ":" or control chars (e.g. newlines/tabs)
        """

        pure_path = PurePosixPath(path)
        if (
            path.startswith("/")
            or ".." in pure_path.parts
            or self._INVALID_PATH_CHARS_RE.search(path) is not None
        ):
            return False
        return True

    def _build_zip(
        self, storage: Any, project_id: UUID, manifest: list[dict[str, str]]
    ) -> str:
        """Materialize a snapshot manifest into a ZIP file using CAS blobs.

        Args:
            storage: Storage backend instance that supports blob checks and reads.
            project_id: Project UUID to resolve the CAS bucket.
            manifest: Snapshot manifest entries with ``path`` and ``hash`` keys.

        Returns:
            Path to the temporary ZIP file.
        """

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp_path = tmp.name
        tmp.close()

        bucket_name = project_experiment_bucket_name(project_id, None)
        missing_blobs = []
        with zipfile.ZipFile(
            tmp_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zipf:
            for entry in manifest:
                path = entry.get("path")
                blob_hash = entry.get("hash")
                if not path or not blob_hash:
                    continue
                if not self._validate_relative_path(path):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Invalid path in snapshot: {path}. "
                            "Path must be relative and not contain '..', start with '/', "
                            "or include ':'/control characters."
                        ),
                    )
                blob_hash = self._normalize_hash(str(blob_hash))
                exists = storage.exists_blob(bucket_name, blob_hash)
                if not exists:
                    missing_blobs.append(f"{path}: {blob_hash}")
                    continue
                response = storage.get_blob(bucket_name, blob_hash)
                try:
                    with zipf.open(path, "w") as dest:
                        for chunk in response.stream(32 * 1024):
                            dest.write(chunk)
                finally:
                    response.close()
                    response.release_conn()
            if missing_blobs:
                zipf.writestr(
                    "__missing_blobs_manifest__.txt", "\n".join(missing_blobs)
                )
        return tmp_path
