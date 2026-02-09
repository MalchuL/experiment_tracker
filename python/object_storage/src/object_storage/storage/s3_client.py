"""AWS S3 storage client used by the CAS service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, BinaryIO

import boto3  # type: ignore[import-not-found]
from botocore.exceptions import ClientError  # type: ignore[import-not-found]

from object_storage.config import get_settings


def _blob_key(blob_hash: str) -> str:
    """Build the S3 object key for a CAS blob hash."""

    return f"blobs/{blob_hash[:2]}/{blob_hash[2:]}"


@dataclass
class S3Storage:
    """Thin wrapper around boto3 for CAS object storage."""

    client: Any
    bucket: str

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not already exist."""

        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchBucket", "NotFound"}:
                self.client.create_bucket(Bucket=self.bucket)
                return
            raise

    def stat_blob(self, blob_hash: str) -> bool:
        """Return True if the blob exists in the configured bucket."""

        try:
            self.client.head_object(Bucket=self.bucket, Key=_blob_key(blob_hash))
            return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def put_blob(self, blob_hash: str, data: BinaryIO, size: int) -> None:
        """Upload a blob stream to S3 using the hash-based key."""

        self.client.upload_fileobj(data, self.bucket, _blob_key(blob_hash))

    def get_blob(self, blob_hash: str):
        """Get a streaming response for the blob object."""

        body = self.client.get_object(Bucket=self.bucket, Key=_blob_key(blob_hash))[
            "Body"
        ]
        return _S3BlobStream(body)


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
    return S3Storage(client=client, bucket=settings.s3_bucket)
