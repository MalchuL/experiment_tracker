"""Execute persisted hparam-importance jobs and track worker transitions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from mltools.clients.backend.client import BackendClient
from mltools.clients.object_storage.client import ModelStorage
from mltools.config.settings import get_settings
from mltools.domain.hparam_importance.analysis import run_analysis
from mltools.workers.celery_app import celery_app
from mltools.db.database import session_maker
from mltools.db.models import HparamImportanceJob, HparamImportanceJobMessage, JobStatus


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp.

    Returns:
        datetime: Current UTC time used for lifecycle timestamps.
    """
    return datetime.now(timezone.utc)


async def _process(job_id: UUID) -> None:
    """Execute one persisted analysis job and finalize its lifecycle state.

    Args:
        job_id: Identifier of the pending job to process.

    Returns:
        None: Results and final lifecycle state are committed to the MLTools database.

    Raises:
        ValueError: If the queued job identifier no longer exists.

    Notes:
        Analysis failures are persisted as a failed job and diagnostic message rather
        than escaping the worker transaction.
    """
    async with session_maker() as session:
        job = await session.scalar(select(HparamImportanceJob).where(HparamImportanceJob.id == job_id))
        if job is None:
            raise ValueError(f"Unknown job {job_id}")
        started = utc_now()
        job.status = JobStatus.RUNNING.value
        job.stage = "fetching_experiments"
        job.progress = 0.05
        job.started_at = started
        await session.commit()
        try:
            settings = get_settings()
            successful = await run_analysis(
                session,
                job,
                backend=BackendClient(settings),
                storage=ModelStorage(settings),
                settings=settings.hparam_importance_settings(),
            )
            if successful == 0:
                raise RuntimeError("All selected metrics failed")
            job.status = JobStatus.COMPLETED.value
            job.stage = "completed"
            job.progress = 1.0
        except Exception as exc:
            await session.rollback()
            job = await session.scalar(select(HparamImportanceJob).where(HparamImportanceJob.id == job_id))
            if job is None:
                raise
            job.status = JobStatus.FAILED.value
            job.stage = "failed"
            job.error_message = str(exc)
            session.add(
                HparamImportanceJobMessage(
                    job_id=job.id,
                    level="error",
                    category="training_failed",
                    message=str(exc),
                )
            )
        finally:
            finished = utc_now()
            job.finished_at = finished
            job.duration_ms = int((finished - started).total_seconds() * 1000)
            await session.commit()


@celery_app.task(name="mltools.process_importance_job")
def process_importance_job(job_id: str) -> None:
    """Celery task wrapper that runs asynchronous job processing.

    Args:
        job_id: Serialized UUID of the persisted job.

    Returns:
        None: The task completes after the async processor commits final state.
    """
    asyncio.run(_process(UUID(job_id)))
"""Celery worker entry points for executing persisted importance-analysis jobs."""
