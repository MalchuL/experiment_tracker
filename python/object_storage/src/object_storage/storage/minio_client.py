from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

from minio import Minio  # type: ignore[import-not-found]
from minio.error import S3Error  # type: ignore[import-not-found]

from object_storage.config import get_settings


def _blob_key(blob_hash: str) -> str:
    return f"blobs/{blob_hash[:2]}/{blob_hash[2:]}"


@dataclass
class MinioStorage:
    client: Minio
    bucket: str

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def stat_blob(self, blob_hash: str) -> bool:
        try:
            self.client.stat_object(self.bucket, _blob_key(blob_hash))
            return True
        except S3Error:
            return False

    def put_blob(self, blob_hash: str, data: BinaryIO, size: int) -> None:
        self.client.put_object(
            self.bucket,
            _blob_key(blob_hash),
            data,
            length=size,
            part_size=10 * 1024 * 1024,
        )

    def get_blob(self, blob_hash: str):
        return self.client.get_object(self.bucket, _blob_key(blob_hash))


def get_minio_storage() -> MinioStorage:
    settings = get_settings()
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    return MinioStorage(client=client, bucket=settings.minio_bucket)
