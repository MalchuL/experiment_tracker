"""Persist and retrieve hparam-importance jobs and related records."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mltools.db.models import (
    HparamImportanceJob,
    HparamImportanceJobMessage,
    HparamImportanceJobParameter,
    HparamImportanceResult,
)


class JobNotFoundError(Exception):
    """Raised when a job does not exist within the requested project."""
    pass


class JobRepository:
    """SQLAlchemy repository for job roots and their persisted analysis outputs."""

    def __init__(self, session: AsyncSession):
        """Bind the repository to a request or worker database session.

        Args:
            session: Async SQLAlchemy session used for all repository operations.

        Result:
            JobRepository bound to the supplied transaction context.
        """
        self.session = session

    async def create(self, job: HparamImportanceJob) -> HparamImportanceJob:
        """Persist and commit a new job root.

        Args:
            job: Pending job entity to persist.

        Returns:
            HparamImportanceJob: Refreshed persisted job with generated identifier.
        """
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get(self, project_id: UUID, job_id: UUID, *, full: bool = False) -> HparamImportanceJob:
        """Load one project-scoped job.

        Args:
            project_id: Project that must own the job.
            job_id: Job identifier to load.
            full: Whether to eager-load parameters, results, and messages.

        Returns:
            HparamImportanceJob: Matching job root.

        Raises:
            JobNotFoundError: If the job is missing or belongs to another project.
        """
        statement = select(HparamImportanceJob).where(
            HparamImportanceJob.id == job_id,
            HparamImportanceJob.project_id == project_id,
        )
        if full:
            statement = statement.options(
                selectinload(HparamImportanceJob.parameters),
                selectinload(HparamImportanceJob.results),
                selectinload(HparamImportanceJob.messages),
            )
        job = (await self.session.execute(statement)).scalar_one_or_none()
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found in project {project_id}")
        return job

    async def list(self, project_id: UUID, limit: int, offset: int) -> tuple[list[HparamImportanceJob], int]:
        """List project job history in reverse creation order.

        Args:
            project_id: Project whose jobs are requested.
            limit: Maximum rows to return.
            offset: Number of newest rows to skip.

        Returns:
            tuple[list[HparamImportanceJob], int]: Page rows and total project count.
        """
        rows = list(
            (
                await self.session.scalars(
                    select(HparamImportanceJob)
                    .where(HparamImportanceJob.project_id == project_id)
                    .order_by(HparamImportanceJob.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(HparamImportanceJob).where(
                    HparamImportanceJob.project_id == project_id
                )
            )
            or 0
        )
        return rows, total

    async def clear_analysis_rows(self, job_id: UUID) -> None:
        """Delete replaceable diagnostics, results, and parameter metadata.

        Args:
            job_id: Job whose generated analysis rows should be cleared.

        Returns:
            None: Deletes are staged in the current transaction.
        """
        for model in (
            HparamImportanceJobMessage,
            HparamImportanceResult,
            HparamImportanceJobParameter,
        ):
            await self.session.execute(delete(model).where(model.job_id == job_id))


def parameters_by_key(job: HparamImportanceJob) -> dict[str, HparamImportanceJobParameter]:
    """Index a fully loaded job's parameter metadata by flattened key.

    Args:
        job: Job with the ``parameters`` relationship loaded.

    Returns:
        dict[str, HparamImportanceJobParameter]: Parameter rows keyed by ``flat_key``.
    """
    return {parameter.flat_key: parameter for parameter in job.parameters}


def results_by_metric(job: HparamImportanceJob) -> dict[tuple[str, str | None], list[HparamImportanceResult]]:
    """Group a fully loaded job's result rows by metric name and label.

    Args:
        job: Job with the ``results`` relationship loaded.

    Returns:
        dict[tuple[str, str | None], list[HparamImportanceResult]]: Result rows grouped
        by exact target metric identity.
    """
    grouped: dict[tuple[str, str | None], list[HparamImportanceResult]] = defaultdict(list)
    for result in job.results:
        grouped[(result.target_metric["name"], result.target_metric.get("label"))].append(result)
    return grouped
"""Persistence operations for hyperparameter-importance jobs and outputs."""
