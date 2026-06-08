"""S3-compatible model-artifact storage adapter for MLTools."""

from .client import ModelStorage, metric_slug, model_artifact_key

__all__ = ["ModelStorage", "metric_slug", "model_artifact_key"]
"""Public exports for MLTools model-artifact storage adapters."""
