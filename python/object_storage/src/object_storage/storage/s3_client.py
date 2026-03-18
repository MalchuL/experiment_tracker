"""AWS S3 storage client used by the CAS service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

import boto3  # type: ignore[import-not-found]
from botocore.exceptions import ClientError  # type: ignore[import-not-found]

from object_storage.config import get_settings


class S3PaginatorProtocol(Protocol):
    def paginate(self, **kwargs): ...


class S3ClientProtocol(Protocol):
    def head_bucket(self, **kwargs) -> None: ...

    def create_bucket(self, **kwargs) -> None: ...

    def delete_bucket(self, **kwargs) -> None: ...

    def head_object(self, **kwargs) -> None: ...

    def upload_fileobj(self, fileobj: BinaryIO, bucket: str, key: str) -> None: ...

    def get_object(self, **kwargs) -> dict[str, object]: ...

    def delete_object(self, **kwargs) -> None: ...

    def get_paginator(self, operation_name: str) -> S3PaginatorProtocol: ...

    def delete_objects(self, **kwargs) -> dict[str, object]: ...


def _blob_key(blob_hash: str) -> str:
    """Build the S3 object key for a CAS blob hash."""

    return f"blobs/{blob_hash[:2]}/{blob_hash[2:]}"


@dataclass
class S3Storage:
    """Thin wrapper around boto3 for CAS object storage."""

    client: S3ClientProtocol

    def ensure_bucket(self, bucket_name: str) -> None:
        """Create the bucket if it does not already exist."""

        try:
            self.client.head_bucket(Bucket=bucket_name)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchBucket", "NotFound"}:
                self.client.create_bucket(Bucket=bucket_name)
                return
            raise

    def delete_bucket(self, bucket_name: str) -> bool:
        """Delete the bucket."""

        self.client.delete_bucket(Bucket=bucket_name)
        return True

    def stat_blob(self, bucket_name: str, blob_hash: str) -> bool:
        """Return True if the blob exists in the configured bucket."""

        try:
            self.client.head_object(Bucket=bucket_name, Key=_blob_key(blob_hash))
            return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def put_blob(
        self, bucket_name: str, blob_hash: str, data: BinaryIO, size: int
    ) -> None:
        """Upload a blob stream to S3 using the hash-based key."""

        self.client.upload_fileobj(data, bucket_name, _blob_key(blob_hash))

    def get_blob(self, bucket_name: str, blob_hash: str):
        """Get a streaming response for the blob object."""

        body = self.client.get_object(Bucket=bucket_name, Key=_blob_key(blob_hash))[
            "Body"
        ]
        return _S3BlobStream(body)

    def delete_blob(self, bucket_name: str, blob_hash: str) -> bool:
        """Delete one blob object by hash."""

        if not self.stat_blob(bucket_name, blob_hash):
            return False
        self.client.delete_object(Bucket=bucket_name, Key=_blob_key(blob_hash))
        return True

    def list_blobs(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List object keys in a bucket optionally filtered by prefix."""

        paginator = self.client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item.get("Key")
                if key:
                    keys.append(str(key))
        return keys

    def delete_blobs(self, bucket_name: str, keys: list[str]) -> int:
        """Delete multiple object keys and return deleted count."""

        if not keys:
            return 0
        deleted_count = 0
        batch_size = 1000
        for i in range(0, len(keys), batch_size):
            chunk = keys[i : i + batch_size]
            response = self.client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": [{"Key": key} for key in chunk], "Quiet": True},
            )
            deleted_count += len(response.get("Deleted", []))
        return deleted_count


class _S3BlobStream:
    """Adapter that provides a MinIO-like streaming interface over boto3."""

    def __init__(self, body) -> None:
        """Store the boto3 streaming body reference."""

        self._body = body

    def stream(self, chunk_size: int):
        """Yield byte chunks from the underlying S3 streaming body."""

        return self._body.iter_chunks(chunk_size=chunk_size)

    def close(self) -> None:
        """Close the underlying S3 streaming body."""

        self._body.close()

    def release_conn(self) -> None:
        """No-op for compatibility with MinIO response objects."""

        return None


def get_s3_storage() -> S3Storage:
    """Provide a configured S3Storage instance for dependency injection."""

    settings = get_settings()
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )
    return S3Storage(client=client)
