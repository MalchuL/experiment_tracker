"""Artifacts storage domain entrypoint."""

from object_storage.domain.artifacts_storage.controller import router

__all__ = ["router"]
