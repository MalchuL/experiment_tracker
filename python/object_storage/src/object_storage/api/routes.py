"""FastAPI routing entrypoint for object and artifacts storage domains."""

from fastapi import APIRouter

from object_storage.domain.artifacts_storage import router as artifacts_router
from object_storage.domain.object_storage import router as object_router

router = APIRouter()
router.include_router(object_router)
router.include_router(artifacts_router)

__all__ = ["router"]
