"""Adapt the domain job-dispatch port to the configured Celery queue."""

from uuid import UUID

from mltools.workers.hparam_importance import process_importance_job


class CeleryJobDispatcher:
    """Dispatch persisted importance jobs to the Celery worker queue."""

    def dispatch(self, job_id: UUID) -> None:
        """Enqueue one persisted hyperparameter-importance job.

        Args:
            job_id: Identifier of the job row the worker must process.

        Returns:
            None: Celery accepts the asynchronous task before this method returns.
        """
        process_importance_job.delay(str(job_id))
"""Celery-backed adapter for the domain job-dispatch protocol."""
