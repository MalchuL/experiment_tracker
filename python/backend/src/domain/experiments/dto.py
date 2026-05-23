import re
from uuid import UUID

from experiment_tracker_shared.limits import (
    ENTITY_DESCRIPTION_MAX_LEN,
    ENTITY_NAME_MAX_LEN,
)
from lib.types import UUID_TYPE
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from models import ExperimentStatus

from lib.datetime_types import ApiDateTime, ApiOptionalDateTime
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse, MAX_LIST_PAGE_SIZE
from lib.category_cleanup_dto import CategoryCleanupResponseDTO


class FeatureNodeDTO(BaseModel):
    name: str = Field(..., min_length=1)
    children: Optional[List["FeatureNodeDTO"]] = None

    model_config = model_config()


class ExperimentBaseDTO(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=ENTITY_NAME_MAX_LEN)
    description: str = Field(
        default="", max_length=ENTITY_DESCRIPTION_MAX_LEN
    )
    status: ExperimentStatus = ExperimentStatus.PLANNED
    parent_experiment_id: Optional[UUID_TYPE] = None
    features: List[FeatureNodeDTO] = Field(default_factory=list)
    color: Optional[str] = None
    order: Optional[int] = None
    tags: Optional[List[str]] = None

    model_config = model_config()

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^#[0-9a-fA-F]{6,8}$", v):
            raise ValueError("Invalid color")
        return v


class ExperimentCreateDTO(ExperimentBaseDTO):
    model_config = model_config()


class ExperimentUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=ENTITY_NAME_MAX_LEN)
    description: Optional[str] = Field(None, max_length=ENTITY_DESCRIPTION_MAX_LEN)
    parent_experiment_id: Optional[UUID_TYPE] = None
    color: Optional[str] = None
    status: Optional[ExperimentStatus] = None
    features: Optional[List[FeatureNodeDTO]] = None
    progress: Optional[int] = None
    order: Optional[int] = None
    tags: Optional[List[str]] = None

    model_config = model_config()

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^#[0-9a-fA-F]{6,8}$", v):
            raise ValueError("Invalid color")
        return v


class ExperimentDTO(ExperimentBaseDTO):
    id: UUID
    progress: int
    created_at: ApiDateTime
    started_at: ApiOptionalDateTime
    completed_at: ApiOptionalDateTime

    model_config = model_config()


class ExperimentListItemDTO(ExperimentDTO):
    features: Optional[List[FeatureNodeDTO]] = None

    model_config = model_config()


class ExperimentDeleteResponseDTO(CategoryCleanupResponseDTO):
    """Outcome of DELETE ``/experiments/{id}`` (cleanup-shaped: ``success``, ``results``, ``errors``)."""

    model_config = model_config()


class UsageBytesCountDTO(BaseModel):
    """Generic ``{count, bytes}`` block reused for artifact groupings in usage DTOs."""

    count: int = 0
    bytes: int = 0

    model_config = model_config()


class ExperimentUsageSnapshotsDTO(BaseModel):
    """Placeholder for future per-experiment snapshot storage accounting."""

    count: int = 0
    bytes: int = 0
    known: bool = False

    model_config = model_config()


class ExperimentScalarsUsageDTO(BaseModel):
    """ClickHouse footprint for the experiment (time-series + metadata tables on scalars)."""

    rows: int = 0
    bytes: int = 0

    model_config = model_config()


class ExperimentUsageTotalDTO(BaseModel):
    """Sum of artifact + at-step + snapshot + scalar bytes returned to the client."""

    bytes: int = 0

    model_config = model_config()


class ExperimentUsageDTO(BaseModel):
    """Unified experiment storage view for dashboards / danger zone lazy loading."""

    experiment_id: str
    project_id: str
    experiment_artifacts: UsageBytesCountDTO
    at_step_artifacts: UsageBytesCountDTO
    snapshots: ExperimentUsageSnapshotsDTO
    scalars: ExperimentScalarsUsageDTO
    total: ExperimentUsageTotalDTO

    model_config = model_config()


class ExperimentListResponseDTO(PaginatedResponse[ExperimentListItemDTO]):
    model_config = model_config()


class ExperimentReorderDTO(BaseModel):
    project_id: UUID
    experiment_ids: List[UUID]

    model_config = model_config()


class ExperimentBatchLookupDTO(BaseModel):
    """Request body for loading specific experiments in a project (same DTOs as list)."""

    experiment_ids: List[UUID] = Field(
        ...,
        min_length=1,
        max_length=MAX_LIST_PAGE_SIZE,
        description="Experiment UUIDs to resolve; must belong to the project in the URL.",
    )

    model_config = model_config()
