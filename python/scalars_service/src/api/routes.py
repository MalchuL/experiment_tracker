from fastapi import APIRouter

from app.domain.last_logged.controller import router as last_logged_router
from app.domain.artifacts_info.controller import router as artifacts_info_router
from app.domain.projects.controller import router as projects_router
from app.domain.scalars.controller import router as scalars_router
from config import get_settings

router = APIRouter()

API_PREFIX = get_settings().API_PREFIX
router.include_router(scalars_router, prefix=API_PREFIX)
router.include_router(artifacts_info_router, prefix=API_PREFIX)
router.include_router(projects_router, prefix=API_PREFIX)
router.include_router(last_logged_router, prefix=API_PREFIX)
