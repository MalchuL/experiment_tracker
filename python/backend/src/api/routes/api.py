from fastapi import APIRouter

from api.routes.auth import router as auth_router
from domain.api_tokens.controller import router as api_tokens_router
from domain.experiments.controller import router as experiments_router
from domain.hypotheses.controller import router as hypotheses_router
from domain.metrics.controller import router as metrics_router
from domain.projects.controller import router as projects_router
from domain.team.teams.controller import router as teams_router
from domain.projects.dashboard.controller import router as dashboard_router

router = APIRouter()

# Align paths with legacy backend/routes.py naming.
API_PREFIX = "/api"
router.include_router(projects_router, prefix=API_PREFIX)
router.include_router(experiments_router, prefix=API_PREFIX)
router.include_router(hypotheses_router, prefix=API_PREFIX)
router.include_router(metrics_router, prefix=API_PREFIX)
router.include_router(teams_router, prefix=API_PREFIX)
router.include_router(dashboard_router, prefix=API_PREFIX)
router.include_router(auth_router)
router.include_router(api_tokens_router)