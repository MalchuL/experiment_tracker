"""Upload trained importance-model artifacts to S3-compatible storage."""

from __future__ import annotations

from io import BytesIO

import boto3

from mltools.config.settings import Settings, get_settings


class ModelStorage:
    """Upload serialized trained-model artifacts to the configured bucket."""

    def __init__(self, settings: Settings | None = None):
        """Initialize the S3-compatible storage adapter.

        Args:
            settings: Optional process settings; cached environment settings are used
                when omitted.

        Result:
            ModelStorage configured with an S3 client and target bucket.
        """
        self.settings = settings or get_settings()
        self.bucket = self.settings.object_storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=self.settings.object_storage_endpoint,
            region_name=self.settings.object_storage_region,
            aws_access_key_id=self.settings.object_storage_access_key,
            aws_secret_access_key=self.settings.object_storage_secret_key,
        )

    def ensure_bucket(self) -> None:
        """Ensure the configured model-artifact bucket exists.

        Returns:
            None: The bucket exists before the method returns.
        """
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            kwargs = {"Bucket": self.bucket}
            if self.settings.object_storage_region != "us-east-1":
                kwargs["CreateBucketConfiguration"] = {
                    "LocationConstraint": self.settings.object_storage_region
                }
            self.client.create_bucket(**kwargs)

    def upload(self, key: str, content: bytes) -> None:
        """Upload a serialized model artifact.

        Args:
            key: Object key within the configured MLTools bucket.
            content: Complete serialized artifact bytes.

        Returns:
            None: Upload completes before returning.
        """
        self.ensure_bucket()
        self.client.upload_fileobj(BytesIO(content), self.bucket, key)


def metric_slug(name: str, label: str | None = None) -> str:
    """Normalize a metric identity for use in an object-storage key.

    Args:
        name: Metric name.
        label: Optional metric label used to disambiguate dimensions.

    Returns:
        str: Lowercase, hyphen-separated, storage-safe slug.
    """
    raw = name if label is None else f"{name}-{label}"
    slug = "".join(character.lower() if character.isalnum() else "-" for character in raw)
    return "-".join(part for part in slug.split("-") if part) or "metric"


def model_artifact_key(project_id: str, job_id: str, name: str, label: str | None) -> str:
    """Build the canonical object key for a trained model artifact.

    Args:
        project_id: Project identifier serialized as text.
        job_id: Importance job identifier serialized as text.
        name: Target metric name.
        label: Optional target metric label.

    Returns:
        str: Canonical project/job/metric-scoped ``model.joblib`` key.
    """
    return (
        f"projects/{project_id}/hparam-importance/jobs/{job_id}/models/"
        f"{metric_slug(name, label)}/model.joblib"
    )
"""S3-compatible model artifact storage adapter for MLTools."""
