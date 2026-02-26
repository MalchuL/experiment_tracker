"""FastAPI routing entrypoint for object and artifacts storage domains."""

from fastapi import APIRouter

from object_storage.domain.experiment_artifacts_storage import (
    router as experiment_artifacts_router,
)
from object_storage.domain.project_artifacts_storage import (
    router as project_artifacts_router,
)

router = APIRouter()
router.include_router(project_artifacts_router)
router.include_router(experiment_artifacts_router)

__all__ = ["router"]
