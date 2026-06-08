"""Aggregate internal MLTools HTTP routers into one API router."""

from fastapi import APIRouter

from mltools.domain.hparam_importance.controller import router as hparam_importance_router

router = APIRouter()
router.include_router(hparam_importance_router)
"""Top-level internal API router composition for MLTools.

The router currently mounts the hyperparameter-importance bounded context and is
the extension point for future ML analysis domains.
"""
