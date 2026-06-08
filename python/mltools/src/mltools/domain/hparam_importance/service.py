"""Implement application use cases for hparam-importance job APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from mltools.domain.hparam_importance.dto import (
    CreateJobDTO,
    CreateJobResponseDTO,
    JobDTO,
    JobListDTO,
    MessageDTO,
    MessagesDTO,
    MetricResultsDTO,
    ResultItemDTO,
    ResultsDTO,
    TargetMetricDTO,
)
from mltools.db.models import HparamImportanceJob, JobStatus
from mltools.domain.hparam_importance.repository import JobRepository, parameters_by_key, results_by_metric
from mltools.domain.hparam_importance.protocol import JobDispatcherProtocol
from mltools.domain.hparam_importance.settings import HparamImportanceSettings


def job_to_dto(job: HparamImportanceJob) -> JobDTO:
    """Map a persisted job root to its API representation.

    Args:
        job: Persisted job entity.

    Returns:
        JobDTO: Validated lifecycle and progress response.
    """
    return JobDTO(
        job_id=job.id,
        project_id=job.project_id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        target_metrics=[TargetMetricDTO.model_validate(item) for item in job.target_metrics],
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        duration_ms=job.duration_ms,
        error_message=job.error_message,
    )


class JobService:
    """Orchestrate job persistence, dispatch, history, results, and diagnostics."""

    def __init__(
        self,
        session: AsyncSession,
        dispatcher: JobDispatcherProtocol,
        settings: HparamImportanceSettings,
    ):
        """Initialize the job application service.

        Args:
            session: Async SQLAlchemy session for job persistence.
            dispatcher: Port used to enqueue persisted jobs.
            settings: Immutable domain analysis configuration.

        Result:
            JobService configured for request handling.
        """
        self.session = session
        self.dispatcher = dispatcher
        self.settings = settings
        self.repository = JobRepository(session)

    def _resolved_config(self, payload: CreateJobDTO) -> dict:
        """Snapshot request overrides and effective settings into job configuration.

        Args:
            payload: Validated job creation request.

        Returns:
            dict: JSON-compatible immutable configuration persisted with the job.
        """
        return {
            "excluded_experiment_ids": [str(item) for item in payload.excluded_experiment_ids],
            "excluded_hparams": payload.excluded_hparams,
            "parameter_overrides": {
                key: value.model_dump(exclude_none=True)
                for key, value in payload.parameter_overrides.items()
            },
            "rf": {
                "n_estimators": self.settings.rf_n_estimators,
                "max_depth": self.settings.rf_max_depth,
                "min_samples_split": self.settings.rf_min_samples_split,
                "min_samples_leaf": self.settings.rf_min_samples_leaf,
                "random_state": self.settings.rf_random_state,
                "n_jobs": self.settings.rf_n_jobs,
                "test_size": self.settings.rf_test_size,
            },
            "preprocessing": {
                "missing_value_strategy": self.settings.missing_value_strategy,
                "default_array_strategy": self.settings.default_array_strategy,
                "default_text_strategy": self.settings.default_text_strategy,
                "path_separator": self.settings.hparam_path_separator,
                "max_category_cardinality": self.settings.max_category_cardinality,
                "min_experiments_per_metric": self.settings.min_experiments_per_metric,
            },
        }

    async def create(self, project_id: UUID, payload: CreateJobDTO) -> CreateJobResponseDTO:
        """Persist a pending job and dispatch it for asynchronous processing.

        Args:
            project_id: Project whose experiments will be analyzed.
            payload: Validated target metrics, exclusions, and parameter overrides.

        Returns:
            CreateJobResponseDTO: New job identifier and initial status.

        Raises:
            Exception: If persistence or dispatch fails. Dispatch failures mark the
            already-persisted job as failed before being re-raised.
        """
        job = await self.repository.create(
            HparamImportanceJob(
                project_id=project_id,
                requested_by_user_id=payload.requested_by_user_id,
                status=JobStatus.PENDING.value,
                stage="created",
                progress=0,
                target_metrics=[item.model_dump() for item in payload.target_metrics],
                config=self._resolved_config(payload),
            )
        )
        try:
            self.dispatcher.dispatch(job.id)
        except Exception as exc:
            job.status = JobStatus.FAILED.value
            job.stage = "failed"
            job.error_message = f"Could not enqueue job: {exc}"
            job.finished_at = datetime.now(timezone.utc)
            await self.session.commit()
            raise
        return CreateJobResponseDTO(job_id=job.id, status=job.status)

    async def get(self, project_id: UUID, job_id: UUID) -> JobDTO:
        """Return one project-scoped job status.

        Args:
            project_id: Project that must own the job.
            job_id: Job identifier.

        Returns:
            JobDTO: Current lifecycle, progress, and timing metadata.
        """
        return job_to_dto(await self.repository.get(project_id, job_id))

    async def list(self, project_id: UUID, limit: int, offset: int) -> JobListDTO:
        """Return paginated job history for a project.

        Args:
            project_id: Project whose job history is requested.
            limit: Maximum jobs to return.
            offset: Number of newest jobs to skip.

        Returns:
            JobListDTO: Page rows and pagination metadata.
        """
        jobs, total = await self.repository.list(project_id, limit, offset)
        return JobListDTO(
            data=[job_to_dto(job) for job in jobs],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def results(self, project_id: UUID, job_id: UUID) -> ResultsDTO:
        """Return ranked results grouped by the job's requested target metrics.

        Args:
            project_id: Project that must own the job.
            job_id: Job whose results are requested.

        Returns:
            ResultsDTO: Target metrics in request order with ranked result items.
        """
        job = await self.repository.get(project_id, job_id, full=True)
        parameters = parameters_by_key(job)
        groups = results_by_metric(job)
        response = []
        for metric in job.target_metrics:
            key = (metric["name"], metric.get("label"))
            items = []
            for result in sorted(groups.get(key, []), key=lambda item: item.rank):
                parameter = parameters.get(result.flat_key)
                items.append(
                    ResultItemDTO(
                        rank=result.rank,
                        flat_key=result.flat_key,
                        path=result.path,
                        importance=result.importance,
                        importance_method=result.importance_method,
                        selected_type=parameter.selected_type if parameter else None,
                        processing_strategy=parameter.processing_strategy if parameter else None,
                    )
                )
            response.append(MetricResultsDTO(target_metric=TargetMetricDTO.model_validate(metric), items=items))
        return ResultsDTO(job_id=job.id, results=response)

    async def messages(self, project_id: UUID, job_id: UUID) -> MessagesDTO:
        """Return persisted diagnostics for one job in creation order.

        Args:
            project_id: Project that must own the job.
            job_id: Job whose messages are requested.

        Returns:
            MessagesDTO: Ordered informational, warning, and error messages.
        """
        job = await self.repository.get(project_id, job_id, full=True)
        return MessagesDTO(
            job_id=job.id,
            messages=[
                MessageDTO(
                    level=item.level,
                    category=item.category,
                    message=item.message,
                    experiment_id=item.experiment_id,
                    flat_key=item.flat_key,
                    target_metric=TargetMetricDTO.model_validate(item.target_metric) if item.target_metric else None,
                    created_at=item.created_at,
                )
                for item in sorted(job.messages, key=lambda message: message.created_at)
            ],
        )
"""Application service for creating and reading hyperparameter-importance jobs."""
