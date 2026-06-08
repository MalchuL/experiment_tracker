"""Build request-scoped application services for MLTools API handlers."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mltools.config.settings import get_settings
from mltools.db.database import get_session
from mltools.domain.hparam_importance.service import JobService
from mltools.workers.dispatcher import CeleryJobDispatcher


def get_job_service(session: AsyncSession = Depends(get_session)) -> JobService:
    """Construct the request-scoped hyperparameter-importance job service.

    Args:
        session: Async SQLAlchemy session supplied by FastAPI for the current request.

    Returns:
        JobService: Application service configured with persistence, Celery dispatch,
        and environment-derived importance-analysis settings.
    """
    return JobService(
        session,
        CeleryJobDispatcher(),
        get_settings().hparam_importance_settings(),
    )
"""FastAPI dependency composition for MLTools application services.

The module connects request-scoped infrastructure to the hyperparameter-importance
bounded context. It contains no analysis behavior; it only constructs services with
their database session, Celery dispatcher, and resolved domain settings.
"""
