"""Storage abstraction for CAS blob backends."""

from __future__ import annotations

from typing import BinaryIO, Protocol

from object_storage.config import get_settings
from object_storage.storage.minio_client import MinioStorage, get_minio_storage
from object_storage.storage.s3_client import S3Storage, get_s3_storage


class StorageBackend(Protocol):
    """Protocol that storage backends must implement for CAS operations."""

    def ensure_bucket(self) -> None:
        """Ensure the target bucket exists."""

    def stat_blob(self, blob_hash: str) -> bool:
        """Check whether a blob exists."""

    def put_blob(self, blob_hash: str, data: BinaryIO, size: int) -> None:
        """Upload a blob stream by hash."""

    def get_blob(self, blob_hash: str):
        """Return a streaming response object for the blob."""


def get_storage() -> StorageBackend:
    """Return the default storage backend (S3 by default)."""

    settings = get_settings()
    backend = getattr(settings, "storage_backend", "s3").lower()
    if backend == "minio":
        return get_minio_storage()
    return get_s3_storage()


__all__ = [
    "StorageBackend",
    "MinioStorage",
    "S3Storage",
    "get_minio_storage",
    "get_s3_storage",
    "get_storage",
]
