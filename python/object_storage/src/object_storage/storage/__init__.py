"""Storage abstraction for CAS blob backends."""

from __future__ import annotations

from typing import BinaryIO, Protocol, cast

from object_storage.storage.dto import BlobListEntry
from object_storage.storage.s3_client import S3Storage, get_s3_storage


class StorageBackend(Protocol):
    """Protocol that storage backends must implement for CAS operations."""

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check whether a bucket exists."""

    def ensure_bucket(self, bucket_name: str) -> None:
        """Ensure the target bucket exists."""

    def delete_bucket(self, bucket_name: str) -> bool:
        """Delete the bucket."""

    def exists_blob(self, bucket_name: str, blob_hash: str) -> bool:
        """Check whether a blob exists."""

    def size_blob(self, bucket_name: str, blob_hash: str) -> int:
        """Get the size of a blob."""

    def put_blob(
        self, bucket_name: str, blob_hash: str, data: BinaryIO, size: int
    ) -> None:
        """Upload a blob stream by hash."""

    def get_blob(self, bucket_name: str, blob_hash: str):
        """Return a streaming response object for the blob."""

    def delete_blob(self, bucket_name: str, blob_hash: str) -> bool:
        """Delete one blob by hash from the bucket."""

    def list_blobs(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List object keys for a bucket and prefix."""

    def list_blob_entries(
        self, bucket_name: str, prefix: str = ""
    ) -> list[BlobListEntry]:
        """List objects (key + size) as reported by the object store list API."""

    def delete_blobs(self, bucket_name: str, keys: list[str]) -> int:
        """Delete many objects from a bucket and return deleted count."""

    def list_bucket_names(self) -> list[str]:
        """List all bucket names in the object store account."""


def get_storage() -> StorageBackend:
    """Return the S3 client used for RustFS and AWS S3."""

    return cast(StorageBackend, get_s3_storage())


__all__ = [
    "BlobListEntry",
    "StorageBackend",
    "S3Storage",
    "get_s3_storage",
    "get_storage",
]
