import httpx
from fastapi import UploadFile


class ObjectStorageClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def check_blobs(self, hashes: list[str]) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/blobs/check", json=hashes)
            response.raise_for_status()
            return response.json()

    async def upload_blob(self, blob_hash: str, upload: UploadFile) -> dict:
        upload.file.seek(0)
        files = {
            "file": (
                upload.filename,
                upload.file,
                upload.content_type or "application/octet-stream",
            )
        }
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}/blobs/upload",
                params={"hash": blob_hash},
                files=files,
            )
            response.raise_for_status()
            return response.json()

    async def create_snapshot(self, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/snapshots", json=payload)
            response.raise_for_status()
            return response.json()
