from __future__ import annotations

import hashlib
import os
import tempfile
import zipfile
from pathlib import PurePosixPath
from uuid import UUID

import anyio
from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from object_storage.api.schemas import (
    BlobCheckResponse,
    SnapshotCreateRequest,
    SnapshotCreateResponse,
)
from object_storage.db import Blob, Experiment, Snapshot, get_async_session
from object_storage.storage import MinioStorage, get_minio_storage

router = APIRouter()


def _validate_relative_path(path: str) -> None:
    pure_path = PurePosixPath(path)
    if path.startswith("/") or ".." in pure_path.parts:
        raise HTTPException(status_code=400, detail="Invalid snapshot path")


async def _spool_upload(
    upload: UploadFile,
) -> tuple[tempfile.SpooledTemporaryFile, int, str]:
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


@router.post("/blobs/check", response_model=BlobCheckResponse)
async def check_blobs(
    hashes: list[str] = Body(..., embed=False),
    session: AsyncSession = Depends(get_async_session),
):
    if not hashes:
        return BlobCheckResponse(missing=[])
    result = await session.execute(select(Blob.hash).where(Blob.hash.in_(hashes)))
    existing = {row[0] for row in result.all()}
    missing = [blob_hash for blob_hash in hashes if blob_hash not in existing]
    return BlobCheckResponse(missing=missing)


@router.post("/blobs/upload")
async def upload_blob(
    hash: str = Query(..., min_length=64, max_length=64),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    storage: MinioStorage = Depends(get_minio_storage),
):
    existing = await session.get(Blob, hash)
    if existing:
        return {"status": "exists"}

    spool: tempfile.SpooledTemporaryFile | None = None
    try:
        spool, size, computed = await _spool_upload(file)
        if computed != hash:
            raise HTTPException(
                status_code=400,
                detail=f"Hash mismatch, computed: {computed}, expected: {hash}",
            )

        await anyio.to_thread.run_sync(storage.put_blob, hash, spool, size)
        session.add(Blob(hash=hash, size=size, ref_count=0))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        return {"status": "ok"}
    finally:
        if spool is not None:
            spool.close()


@router.post("/snapshots", response_model=SnapshotCreateResponse)
async def create_snapshot(
    payload: SnapshotCreateRequest,
    session: AsyncSession = Depends(get_async_session),
):
    hashes = [entry.hash for entry in payload.files]
    if hashes:
        result = await session.execute(select(Blob.hash).where(Blob.hash.in_(hashes)))
        existing = {row[0] for row in result.all()}
        missing = [blob_hash for blob_hash in hashes if blob_hash not in existing]
        if missing:
            raise HTTPException(
                status_code=400, detail=f"Missing blobs: {', '.join(missing)}"
            )

    result = await session.execute(
        select(Experiment).where(Experiment.name == payload.experiment_name)
    )
    experiment = result.scalars().first()
    if experiment is None:
        experiment = Experiment(name=payload.experiment_name)
        session.add(experiment)
        await session.flush()

    snapshot = Snapshot(
        experiment_id=experiment.id,
        manifest=[entry.model_dump() for entry in payload.files],
    )
    session.add(snapshot)

    if hashes:
        await session.execute(
            update(Blob)
            .where(Blob.hash.in_(hashes))
            .values(ref_count=Blob.ref_count + 1)
        )

    await session.commit()
    await session.refresh(snapshot)
    return SnapshotCreateResponse(snapshot_id=str(snapshot.id))


def _build_zip(storage: MinioStorage, manifest: list[dict]) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = tmp.name
    tmp.close()

    with zipfile.ZipFile(tmp_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for entry in manifest:
            path = entry.get("path")
            blob_hash = entry.get("hash")
            if not path or not blob_hash:
                continue
            _validate_relative_path(path)
            response = storage.get_blob(blob_hash)
            try:
                with zipf.open(path, "w") as dest:
                    for chunk in response.stream(32 * 1024):
                        dest.write(chunk)
            finally:
                response.close()
                response.release_conn()
    return tmp_path


@router.get("/snapshots/{snapshot_id}/download")
async def download_snapshot(
    snapshot_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    storage: MinioStorage = Depends(get_minio_storage),
):
    result = await session.execute(select(Snapshot).where(Snapshot.id == snapshot_id))
    snapshot = result.scalars().first()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    zip_path = await anyio.to_thread.run_sync(_build_zip, storage, snapshot.manifest)
    filename = f"snapshot-{snapshot_id}.zip"

    def _cleanup() -> None:
        if os.path.exists(zip_path):
            os.remove(zip_path)

    return StreamingResponse(
        open(zip_path, "rb"),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        background=BackgroundTask(_cleanup),
    )
