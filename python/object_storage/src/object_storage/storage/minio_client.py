from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID

from minio import Minio  # type: ignore[import-not-found]
from minio.error import S3Error  # type: ignore[import-not-found]
from minio.deleteobjects import DeleteObject  # type: ignore[import-not-found]

from object_storage.config import get_settings
from object_storage.storage.dto import BlobListEntry


def _blob_key(blob_hash: str) -> str:
    """Build the MinIO object key for a CAS blob hash.

    Keys are stored with a lowercase hex hash; callers may pass mixed case.
    """

    h = blob_hash.strip().lower()
    if len(h) < 2:
        return f"blobs/{h}"
    return f"blobs/{h[:2]}/{h[2:]}"


@dataclass
class MinioStorage:
    client: Minio

    def bucket_exists(self, bucket_name: str) -> bool:
        return self.client.bucket_exists(bucket_name)

    def ensure_bucket(self, bucket_name: str) -> None:
        """Create the target bucket if it does not already exist."""

        if not self.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def delete_bucket(self, bucket_name: str) -> bool:
        """Delete the bucket."""

        self.client.remove_bucket(bucket_name)
        return True

    def exists_blob(self, bucket_name: str, blob_hash: str) -> bool:
        """Return True if a blob exists in MinIO for the given hash."""

        try:
            self.client.stat_object(bucket_name, _blob_key(blob_hash))
            return True
        except S3Error:
            return False

    def size_blob(self, bucket_name: str, blob_hash: str) -> int:
        """Get the size of a blob."""

        return self.client.stat_object(bucket_name, _blob_key(blob_hash)).size

    def put_blob(
        self, bucket_name: str, blob_hash: str, data: BinaryIO, size: int
    ) -> None:
        """Upload a blob stream into MinIO under its content hash."""

        self.client.put_object(
            bucket_name,
            _blob_key(blob_hash),
            data,
            length=size,
            part_size=10 * 1024 * 1024,
        )

    def get_blob(self, bucket_name: str, blob_hash: str):
        """Fetch a blob stream from MinIO by its content hash."""

        try:
            return self.client.get_object(bucket_name, _blob_key(blob_hash))
        except S3Error as exc:
            if getattr(exc, "code", "") == "NoSuchKey":
                raise ValueError(
                    f"Blob not found for hash {blob_hash.strip()!r} in bucket {bucket_name!r}"
                ) from exc
            raise

    def delete_blob(self, bucket_name: str, blob_hash: str) -> bool:
        """Delete one blob by hash from MinIO."""

        if not self.exists_blob(bucket_name, blob_hash):
            return False
        self.client.remove_object(bucket_name, _blob_key(blob_hash))
        return True

    def list_blob_entries(
        self, bucket_name: str, prefix: str = ""
    ) -> list[BlobListEntry]:
        """List objects with sizes from MinIO listing (no per-object stat)."""

        entries: list[BlobListEntry] = []
        for obj in self.client.list_objects(
            bucket_name, prefix=prefix, recursive=True
        ):
            if obj is None or not getattr(obj, "object_name", None):
                continue
            entries.append(
                BlobListEntry(
                    key=obj.object_name,
                    size=int(getattr(obj, "size", 0) or 0),
                )
            )
        return entries

    def list_blobs(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List object keys from MinIO with optional prefix."""

        return [e.key for e in self.list_blob_entries(bucket_name, prefix)]

    def list_bucket_names(self) -> list[str]:
        return sorted(b.name for b in self.client.list_buckets())

    def delete_blobs(self, bucket_name: str, keys: list[str]) -> int:
        """Delete many object keys from MinIO and return deleted count."""

        if not keys:
            return 0
        errors = list(
            self.client.remove_objects(bucket_name, [DeleteObject(key) for key in keys])
        )
        return len(keys) - len(errors)


def get_minio_storage() -> MinioStorage:
    """Provide a configured MinioStorage instance for dependency injection."""

    settings = get_settings()
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    return MinioStorage(client=client)
