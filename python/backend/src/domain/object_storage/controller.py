import httpx
from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from starlette.responses import StreamingResponse

from api.routes.auth import get_current_user_dual
from config.settings import get_settings
from domain.object_storage.client import ObjectStorageClient
from domain.object_storage.dto import (
    BlobCheckResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
)
from models import User

router = APIRouter(tags=["object_storage"])


def _raise_object_storage_error(error: Exception) -> None:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        detail = error.response.text
        raise HTTPException(status_code=status, detail=detail)
    if isinstance(error, httpx.RequestError):
        raise HTTPException(status_code=502, detail="Object storage service unavailable")
    raise HTTPException(status_code=400, detail=str(error))


@router.post("/blobs/check", response_model=BlobCheckResponseDTO)
async def check_blobs(
    hashes: list[str] = Body(..., embed=False),
    _user: User = Depends(get_current_user_dual),
):
    client = ObjectStorageClient(get_settings().object_storage_service_url)
    try:
        result = await client.check_blobs(hashes)
        return BlobCheckResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_object_storage_error(exc)


@router.post("/blobs/upload")
async def upload_blob(
    hash: str = Query(..., min_length=64, max_length=64),
    file: UploadFile = File(...),
    _user: User = Depends(get_current_user_dual),
):
    client = ObjectStorageClient(get_settings().object_storage_service_url)
    try:
        return await client.upload_blob(hash, file)
    except Exception as exc:  # noqa: BLE001
        _raise_object_storage_error(exc)


@router.post("/snapshots", response_model=SnapshotCreateResponseDTO)
async def create_snapshot(
    payload: SnapshotCreateRequestDTO,
    _user: User = Depends(get_current_user_dual),
):
    client = ObjectStorageClient(get_settings().object_storage_service_url)
    try:
        result = await client.create_snapshot(payload.model_dump())
        return SnapshotCreateResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_object_storage_error(exc)


@router.get("/snapshots/{snapshot_id}/download")
async def download_snapshot(
    snapshot_id: str,
    _user: User = Depends(get_current_user_dual),
):
    base_url = get_settings().object_storage_service_url.rstrip("/")
    client = httpx.AsyncClient(timeout=None)
    try:
        response = await client.get(
            f"{base_url}/snapshots/{snapshot_id}/download", timeout=None
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        await client.aclose()
        _raise_object_storage_error(exc)

    async def _iter_stream():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    headers = {}
    if "content-disposition" in response.headers:
        headers["Content-Disposition"] = response.headers["content-disposition"]

    return StreamingResponse(
        _iter_stream(),
        media_type=response.headers.get("content-type", "application/zip"),
        headers=headers,
    )
