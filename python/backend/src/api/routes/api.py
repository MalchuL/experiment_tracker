from fastapi import APIRouter

from api.routes.auth import router as auth_router
from config.settings import get_settings
from domain.api_tokens.controller import router as api_tokens_router
from domain.experiments.controller import router as experiments_router
from domain.hypotheses.controller import router as hypotheses_router
from domain.metrics.controller import router as metrics_router
from domain.scalars.controller import router as scalars_router
from domain.projects.controller import router as projects_router
from domain.team.teams.controller import router as teams_router
from domain.projects.dashboard.controller import router as dashboard_router
from domain.object_storage.controller import router as object_storage_router

router = APIRouter()

# Align paths with legacy backend/routes.py naming.
API_PREFIX = get_settings().api_prefix
router.include_router(projects_router)
router.include_router(experiments_router)
router.include_router(hypotheses_router)
router.include_router(metrics_router)
router.include_router(scalars_router)
router.include_router(teams_router)
router.include_router(dashboard_router)
router.include_router(auth_router)
router.include_router(api_tokens_router)
router.include_router(object_storage_router)