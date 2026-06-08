"""Configure the Celery application used by asynchronous MLTools workers."""

from celery import Celery

from mltools.config.settings import get_settings

settings = get_settings()
celery_app = Celery(
    "mltools",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["mltools.workers.hparam_importance"],
)
"""Celery application configuration for asynchronous MLTools jobs."""
