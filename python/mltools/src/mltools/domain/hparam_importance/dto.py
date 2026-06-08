"""Define validated request and response contracts for importance jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TargetMetricDTO(BaseModel):
    """Exact target metric identity selected for analysis.

    Result:
        Validated metric name and optional label pair.
    """
    name: str = Field(min_length=1, max_length=512)
    label: str | None = None


class ParameterOverrideDTO(BaseModel):
    """Optional user override for one flattened hyperparameter.

    Result:
        Selected type, processing strategy, and/or array strategy overrides.
    """
    selected_type: str | None = None
    processing_strategy: str | None = None
    array_strategy: Literal["skip", "flatten_by_index", "stringify_category"] | None = None


class CreateJobDTO(BaseModel):
    """Request payload for creating a hyperparameter-importance job."""
    target_metrics: list[TargetMetricDTO] = Field(min_length=1, max_length=100)
    excluded_experiment_ids: list[UUID] = Field(default_factory=list)
    excluded_hparams: list[str] = Field(default_factory=list)
    parameter_overrides: dict[str, ParameterOverrideDTO] = Field(default_factory=dict)
    requested_by_user_id: UUID | None = None

    @field_validator("target_metrics")
    @classmethod
    def unique_metrics(cls, values: list[TargetMetricDTO]) -> list[TargetMetricDTO]:
        """Reject duplicate target metric name/label pairs.

        Args:
            values: Parsed target metrics from the create-job payload.

        Returns:
            list[TargetMetricDTO]: Original metrics when every identity is unique.

        Raises:
            ValueError: If the request repeats a metric name/label pair.
        """
        keys = [(item.name, item.label) for item in values]
        if len(keys) != len(set(keys)):
            raise ValueError("target_metrics must be unique")
        return values


class CreateJobResponseDTO(BaseModel):
    """Minimal response returned after an analysis job is persisted and queued."""
    job_id: UUID
    status: str


class JobDTO(BaseModel):
    """Job lifecycle and progress representation returned by status endpoints."""
    job_id: UUID
    project_id: UUID
    status: str
    stage: str
    progress: float
    target_metrics: list[TargetMetricDTO]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    error_message: str | None


class JobListDTO(BaseModel):
    """Paginated project job-history response."""
    data: list[JobDTO]
    total: int
    limit: int
    offset: int


class ResultItemDTO(BaseModel):
    """One ranked hyperparameter importance result."""
    rank: int
    flat_key: str
    path: list[str]
    importance: float
    importance_method: str
    selected_type: str | None = None
    processing_strategy: str | None = None


class MetricResultsDTO(BaseModel):
    """All ranked importance results for one selected target metric."""
    target_metric: TargetMetricDTO
    items: list[ResultItemDTO]


class ResultsDTO(BaseModel):
    """Complete grouped importance-results response for one job."""
    job_id: UUID
    results: list[MetricResultsDTO]


class MessageDTO(BaseModel):
    """One persisted job diagnostic message."""
    level: str
    category: str
    message: str
    experiment_id: UUID | None
    flat_key: str | None
    target_metric: TargetMetricDTO | None
    created_at: datetime


class MessagesDTO(BaseModel):
    """Complete ordered diagnostic-message response for one job."""
    job_id: UUID
    messages: list[MessageDTO]


def metric_dict(metric: TargetMetricDTO | dict[str, Any]) -> dict[str, Any]:
    """Normalize a target metric DTO or mapping into a JSON-compatible mapping.

    Args:
        metric: Target metric represented as a DTO or existing mapping.

    Returns:
        dict[str, Any]: Metric identity suitable for JSON persistence.
    """
    return metric.model_dump() if isinstance(metric, TargetMetricDTO) else metric
"""Validated HTTP and application DTOs for hyperparameter-importance jobs."""
