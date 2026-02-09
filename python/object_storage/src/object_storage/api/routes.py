"""FastAPI routing entrypoint for the object storage domain."""

from object_storage.domain.object_storage import router

__all__ = ["router"]
