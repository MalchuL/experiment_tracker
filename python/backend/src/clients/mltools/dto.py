"""Define main-backend DTOs for MLTools proxy requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from lib.dto_config import model_config


class MLToolsTargetMetricDTO(BaseModel):
    """Exact target metric name and optional label."""
    name: str = Field(min_length=1, max_length=512)
    label: str | None = None
    model_config = model_config()


class MLToolsParameterOverrideDTO(BaseModel):
    """Optional processing override for one flattened hyperparameter."""
    selected_type: str | None = None
    processing_strategy: str | None = None
    array_strategy: Literal["skip", "flatten_by_index", "stringify_category"] | None = None
    model_config = model_config()


class MLToolsCreateJobDTO(BaseModel):
    """Validated request sent by the backend when creating an MLTools job."""
    target_metrics: list[MLToolsTargetMetricDTO] = Field(min_length=1, max_length=100)
    excluded_experiment_ids: list[UUID] = Field(default_factory=list)
    excluded_hparams: list[str] = Field(default_factory=list)
    parameter_overrides: dict[str, MLToolsParameterOverrideDTO] = Field(default_factory=dict)
    requested_by_user_id: UUID | None = None
    model_config = model_config()

    @field_validator("target_metrics")
    @classmethod
    def unique_metrics(cls, values: list[MLToolsTargetMetricDTO]) -> list[MLToolsTargetMetricDTO]:
        """Reject duplicate target metric identities.

        Args:
            values: Parsed target metrics.

        Returns:
            list[MLToolsTargetMetricDTO]: Original values when unique.

        Raises:
            ValueError: If a name/label pair is repeated.
        """
        keys = [(item.name, item.label) for item in values]
        if len(keys) != len(set(keys)):
            raise ValueError("target_metrics must be unique")
        return values


class MLToolsCreateJobResponseDTO(BaseModel):
    """Response returned after MLTools persists and queues a job."""
    job_id: UUID
    status: str
    model_config = model_config()


class MLToolsJobDTO(BaseModel):
    """Current lifecycle, progress, target, and timing metadata for a job."""
    job_id: UUID
    project_id: UUID
    status: str
    stage: str
    progress: float
    target_metrics: list[MLToolsTargetMetricDTO]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    error_message: str | None
    model_config = model_config()


class MLToolsJobListDTO(BaseModel):
    """Paginated project MLTools job-history response."""
    data: list[MLToolsJobDTO]
    total: int
    limit: int
    offset: int
    model_config = model_config()


class MLToolsResultItemDTO(BaseModel):
    """One ranked hyperparameter importance result."""
    rank: int
    flat_key: str
    path: list[str]
    importance: float
    importance_method: str
    selected_type: str | None = None
    processing_strategy: str | None = None
    model_config = model_config()


class MLToolsMetricResultsDTO(BaseModel):
    """All ranked result items for one target metric."""
    target_metric: MLToolsTargetMetricDTO
    items: list[MLToolsResultItemDTO]
    model_config = model_config()


class MLToolsResultsDTO(BaseModel):
    """Complete grouped importance-results response for one job."""
    job_id: UUID
    results: list[MLToolsMetricResultsDTO]
    model_config = model_config()


class MLToolsMessageDTO(BaseModel):
    """One persisted MLTools job diagnostic."""
    level: str
    category: str
    message: str
    experiment_id: UUID | None
    flat_key: str | None
    target_metric: MLToolsTargetMetricDTO | None
    created_at: datetime
    model_config = model_config()


class MLToolsMessagesDTO(BaseModel):
    """Complete ordered diagnostic-message response for one job."""
    job_id: UUID
    messages: list[MLToolsMessageDTO]
    model_config = model_config()
"""Main-backend DTO contracts for trusted internal MLTools HTTP calls."""
