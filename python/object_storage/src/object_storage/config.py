from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ML Experiment Object Storage"
    api_prefix: str = "/api"
    allowed_origins: str = "*"

    database_url: str = (
        "postgresql+asyncpg://object_storage:object_storage@localhost:5433/object_storage"
    )

    storage_backend: str = "s3"

    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket: str = "ml-blobs"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_secure: bool = False
    minio_bucket: str = "ml-blobs"

    class Config:
        env_prefix = ""
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache configuration for the CAS service."""

    return Settings()
