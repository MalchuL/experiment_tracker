"""Business logic for CAS blob storage and snapshot creation."""

from __future__ import annotations

import re
import tempfile
import zipfile
from pathlib import PurePosixPath
from uuid import UUID

import anyio
from fastapi import HTTPException, UploadFile
from experiment_tracker_shared import (
    create_sha256_hasher,
)  # pyright: ignore[reportMissingImports]
from sqlalchemy.exc import IntegrityError

from . import mapper
from .dto import (
    BlobCheckResponseDTO,
    DeleteBlobResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadBlobResponseDTO,
)
from .repository import ObjectStorageRepository
from object_storage.domain.buckets.service import (
    BucketRegistryService,
    project_experiment_bucket_name,
)


class ObjectStorageService:
    _SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")
    _INVALID_PATH_CHARS_RE = re.compile(r"[:\x00-\x1f]")

    # 10MB for spooled uploads (temporary file on RAM memory)
    MAX_SPOOL_SIZE = 10 * 1024 * 1024

    # 1MB for chunked uploads (streaming from the client)
    MAX_CHUNK_SIZE = 1024 * 1024

    """CAS workflow service for blob checking, uploads, and snapshots."""

    def __init__(
        self,
        repository: ObjectStorageRepository,
        buckets_service: BucketRegistryService,
    ) -> None:
        """Initialize with metadata repository and project-scoped bucket registry."""

        self._repository = repository
        self._buckets_service = buckets_service

    async def delete_project(self, project_id: UUID) -> bool:
        """Delete a project and all its blobs."""

        await self._buckets_service.delete_all_project_buckets(project_id)
        await self._repository.delete_all_blobs(project_id)
        await self._repository.delete_all_snapshots(project_id)
        await self._repository.commit()
        return True

    async def check_project_blobs(
        self, project_id: UUID, hashes: list[str]
    ) -> BlobCheckResponseDTO:
        """Return hashes that are missing from CAS metadata storage."""

        await self._buckets_service.ensure_bucket(project_id, None)
        if not hashes:
            return mapper.missing_hashes_to_response([])
        normalized_hashes = [self._normalize_hash(blob_hash) for blob_hash in hashes]
        existing = await self._repository.fetch_existing_blob_hashes(
            project_id, normalized_hashes
        )
        missing = [
            blob_hash for blob_hash in normalized_hashes if blob_hash not in existing
        ]
        return mapper.missing_hashes_to_response(missing)

    async def upload_project_blob(
        self, project_id: UUID, blob_hash: str, upload: UploadFile
    ) -> UploadBlobResponseDTO:
        """Upload a blob into CAS storage after verifying its hash."""

        blob_hash = self._normalize_hash(blob_hash)
        existing = await self._repository.fetch_blob(project_id, blob_hash)
        if existing:
            return mapper.upload_status_to_response("exists")

        spool: tempfile.SpooledTemporaryFile | None = None
        try:
            await self._buckets_service.ensure_bucket(project_id, None)
            spool, size, computed = await self._spool_upload(upload)
            if computed != blob_hash:
                raise HTTPException(
                    status_code=400,
                    detail=f"Hash mismatch, computed: {computed}, expected: {blob_hash}",
                )

            spool.seek(0)
            upload_for_bucket = UploadFile(
                filename=upload.filename,
                file=spool,
                headers=upload.headers,
            )
            await self._buckets_service.upload_blob(
                project_id, None, upload_for_bucket, blob_hash
            )
            await self._repository.add_blob(
                project_id,
                blob_hash,
                size,
                upload.content_type or "application/octet-stream",
            )
            try:
                await self._repository.commit()
            except IntegrityError:
                await self._repository.rollback()
                await self._buckets_service.delete_blob(project_id, None, blob_hash)
                raise HTTPException(
                    status_code=500, detail="Failed to add blob to repository"
                )
            return mapper.upload_status_to_response("ok")
        finally:
            if spool is not None:
                spool.close()

    async def create_project_snapshot(
        self, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        """Create a snapshot that points to existing CAS blob hashes."""

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
            existing = await self._repository.fetch_existing_blob_hashes(
                payload.project_id, hashes
            )
            missing = [blob_hash for blob_hash in hashes if blob_hash not in existing]
            if missing:
                raise HTTPException(
                    status_code=400, detail=f"Missing blobs: {', '.join(missing)}"
                )

        manifest = mapper.snapshot_files_to_manifest(normalized_files)
        snapshot = await self._repository.create_snapshot(payload.project_id, manifest)
        if hashes:
            await self._repository.increment_blob_ref_counts(payload.project_id, hashes)
        await self._repository.commit()
        await self._repository.refresh(snapshot)
        return mapper.snapshot_id_to_response(snapshot.id)

    async def delete_project_snapshot(
        self, project_id: UUID, snapshot_id: UUID
    ) -> list[str]:
        """Delete a snapshot and all its blobs."""

        snapshot = await self._repository.fetch_snapshot(snapshot_id)
        if snapshot is None:
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
        return deleted_blobs

    async def prepare_project_snapshot_download(
        self, project_id: UUID, snapshot_id: UUID
    ) -> tuple[str, str]:
        """Create a ZIP archive for a snapshot and return its path and filename."""

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

    async def get_project_blob_stream(self, project_id: UUID, blob_hash: str):
        """Return a streaming handle for a CAS blob by hash."""

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
        return mapper.delete_blob_to_response(deleted_metadata or deleted_storage)

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

    def _build_zip(
        self, storage, project_id: UUID, manifest: list[dict]
    ) -> str:
        """Materialize a snapshot manifest into a ZIP file using CAS blobs."""

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
