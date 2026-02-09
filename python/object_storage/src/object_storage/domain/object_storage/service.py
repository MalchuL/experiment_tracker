"""Business logic for CAS blob storage and snapshot creation."""

from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import PurePosixPath
from uuid import UUID

import anyio
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from object_storage.domain.object_storage import mapper
from object_storage.domain.object_storage.dto import (
    BlobCheckResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadBlobResponseDTO,
)
from object_storage.domain.object_storage.repository import ObjectStorageRepository
from object_storage.storage import StorageBackend


class ObjectStorageService:
    """CAS workflow service for blob checking, uploads, and snapshots."""

    def __init__(
        self, repository: ObjectStorageRepository, storage: StorageBackend
    ) -> None:
        """Initialize with a repository for metadata and a MinIO storage client."""

        self._repository = repository
        self._storage = storage

    async def check_blobs(self, hashes: list[str]) -> BlobCheckResponseDTO:
        """Return hashes that are missing from CAS metadata storage."""

        if not hashes:
            return mapper.missing_hashes_to_response([])
        existing = await self._repository.fetch_existing_blob_hashes(hashes)
        missing = [blob_hash for blob_hash in hashes if blob_hash not in existing]
        return mapper.missing_hashes_to_response(missing)

    async def upload_blob(
        self, blob_hash: str, upload: UploadFile
    ) -> UploadBlobResponseDTO:
        """Upload a blob into CAS storage after verifying its hash."""

        existing = await self._repository.fetch_blob(blob_hash)
        if existing:
            return mapper.upload_status_to_response("exists")

        spool: tempfile.SpooledTemporaryFile | None = None
        try:
            spool, size, computed = await self._spool_upload(upload)
            if computed != blob_hash:
                raise HTTPException(
                    status_code=400,
                    detail=f"Hash mismatch, computed: {computed}, expected: {blob_hash}",
                )

            await anyio.to_thread.run_sync(
                self._storage.put_blob, blob_hash, spool, size
            )
            await self._repository.add_blob(blob_hash, size)
            try:
                await self._repository.commit()
            except IntegrityError:
                await self._repository.rollback()
            return mapper.upload_status_to_response("ok")
        finally:
            if spool is not None:
                spool.close()

    async def create_snapshot(
        self, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        """Create a snapshot that points to existing CAS blob hashes."""

        hashes = [entry.hash for entry in payload.files]
        if hashes:
            existing = await self._repository.fetch_existing_blob_hashes(hashes)
            missing = [blob_hash for blob_hash in hashes if blob_hash not in existing]
            if missing:
                raise HTTPException(
                    status_code=400, detail=f"Missing blobs: {', '.join(missing)}"
                )

        experiment = await self._repository.get_or_create_experiment(
            payload.experiment_name
        )
        snapshot = await self._repository.create_snapshot(
            experiment.id, mapper.snapshot_files_to_manifest(payload.files)
        )
        if hashes:
            await self._repository.increment_blob_ref_counts(hashes)
        await self._repository.commit()
        await self._repository.refresh(snapshot)
        return mapper.snapshot_id_to_response(snapshot.id)

    async def prepare_snapshot_download(self, snapshot_id: UUID) -> tuple[str, str]:
        """Create a ZIP archive for a snapshot and return its path and filename."""

        snapshot = await self._repository.fetch_snapshot(snapshot_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        zip_path = await anyio.to_thread.run_sync(
            self._build_zip, self._storage, snapshot.manifest
        )
        filename = f"snapshot-{snapshot_id}.zip"
        return zip_path, filename

    def _validate_relative_path(self, path: str) -> None:
        """Reject absolute or parent-traversing paths in snapshot manifests."""

        pure_path = PurePosixPath(path)
        if path.startswith("/") or ".." in pure_path.parts:
            raise HTTPException(status_code=400, detail="Invalid snapshot path")

    async def _spool_upload(
        self, upload: UploadFile
    ) -> tuple[tempfile.SpooledTemporaryFile, int, str]:
        """Stream the upload into a spooled file while computing its SHA-256 hash."""

        hasher = hashlib.sha256()
        size = 0
        spool = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            hasher.update(chunk)
            spool.write(chunk)
        spool.seek(0)
        return spool, size, hasher.hexdigest()

    def _build_zip(self, storage: StorageBackend, manifest: list[dict]) -> str:
        """Materialize a snapshot manifest into a ZIP file using CAS blobs."""

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp_path = tmp.name
        tmp.close()

        with zipfile.ZipFile(
            tmp_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zipf:
            for entry in manifest:
                path = entry.get("path")
                blob_hash = entry.get("hash")
                if not path or not blob_hash:
                    continue
                self._validate_relative_path(path)
                response = storage.get_blob(blob_hash)
                try:
                    with zipf.open(path, "w") as dest:
                        for chunk in response.stream(32 * 1024):
                            dest.write(chunk)
                finally:
                    response.close()
                    response.release_conn()
        return tmp_path
