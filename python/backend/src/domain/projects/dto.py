from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse
from lib.satellite_step_dto import SatelliteStepDTO
from lib.category_cleanup_dto import CategoryCleanupResponseDTO
from models import MetricAggregation, MetricDirection


class ProjectOwnerDTO(BaseModel):
    id: UUID
    email: Optional[str] = None
    display_name: Optional[str] = None

    model_config = model_config()


class ProjectTeamDTO(BaseModel):
    id: UUID
    name: Optional[str] = None

    model_config = model_config()


class ProjectMetricDTO(BaseModel):
    name: str
    direction: MetricDirection
    aggregation: MetricAggregation
    label: str | None = None

    model_config = model_config()


class ProjectMetricKeyDTO(BaseModel):
    name: str
    label: str | None = None

    model_config = model_config()


class ProjectMetricsDTO(BaseModel):
    tracked_metrics: List[ProjectMetricDTO] = []
    display_metrics: List[ProjectMetricKeyDTO] = []

    model_config = model_config()

    @field_validator("display_metrics", mode="before")
    @classmethod
    def _coerce_display_metrics_legacy(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        out: list[object] = []
        for item in v:
            if isinstance(item, str):
                out.append({"name": item, "label": None})
            else:
                out.append(item)
        return out


class ProjectSettingType(str, Enum):
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    JSON = "json"


class ProjectSettingDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    type: ProjectSettingType
    value: Any

    model_config = model_config()


class ProjectBaseDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    metrics: ProjectMetricsDTO = ProjectMetricsDTO()
    settings: List[ProjectSettingDTO] = []

    model_config = model_config()


class ProjectDTO(ProjectBaseDTO):
    id: UUID
    owner: Optional[ProjectOwnerDTO] = None
    created_at: ApiDateTime
    experiment_count: int = 0
    hypothesis_count: int = 0
    team: Optional[ProjectTeamDTO] = None

    model_config = model_config()


class ProjectListResponseDTO(PaginatedResponse[ProjectDTO]):
    model_config = model_config()


class ProjectDataDTO(ProjectBaseDTO):
    id: UUID
    team_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None


class ProjectUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    metrics: Optional[ProjectMetricsDTO] = None
    settings: Optional[List[ProjectSettingDTO]] = None

    model_config = model_config()


class ProjectCreateDTO(ProjectBaseDTO):
    team_id: Optional[UUID] = None

    model_config = model_config()


class ProjectSettingValueUpdateDTO(BaseModel):
    value: Any

    model_config = model_config()


class UsageBytesCountDTO(BaseModel):
    """Simple usage block reused across project usage sections."""

    count: int = 0
    bytes: int = 0

    model_config = model_config()


class ProjectUsageScalarTableDTO(BaseModel):
    """One ClickHouse table row in the scalars section of project usage."""

    table: str
    exists: bool
    rows: int
    columns: int
    bytes: int

    model_config = model_config()


class ProjectUsageScalarsDTO(BaseModel):
    """Scalars-service usage section in project usage responses."""

    bytes: int = 0
    tables: list[ProjectUsageScalarTableDTO] = Field(default_factory=list)

    model_config = model_config()


class ProjectUsageExperimentBucketsDTO(BaseModel):
    """Experiment-buckets section in project usage responses."""

    count: int = 0
    bytes: int = 0
    buckets: list[dict[str, Any]] = Field(default_factory=list)

    model_config = model_config()


class ProjectUsageTotalDTO(BaseModel):
    """Total project usage aggregate."""

    bytes: int = 0

    model_config = model_config()


class ProjectUsageDTO(BaseModel):
    """Project usage API response (object storage + scalars)."""

    project_id: str
    project_artifacts: UsageBytesCountDTO
    snapshots: UsageBytesCountDTO
    experiment_buckets: ProjectUsageExperimentBucketsDTO
    scalars: ProjectUsageScalarsDTO
    total: ProjectUsageTotalDTO

    model_config = model_config()


class ExperimentSatelliteTeardownDTO(BaseModel):
    """Per-experiment object storage + scalars outcomes during project teardown."""

    experiment_id: UUID
    object_storage: SatelliteStepDTO
    scalars: SatelliteStepDTO

    model_config = model_config()


class ProjectSatelliteTeardownDTO(BaseModel):
    """All satellite steps for one project before its Postgres row is removed."""

    project_id: UUID
    experiments: list[ExperimentSatelliteTeardownDTO] = Field(default_factory=list)
    project_object_storage: SatelliteStepDTO
    project_scalars: SatelliteStepDTO
    satellites_ok: bool

    model_config = model_config()


class ProjectDeleteResponseDTO(CategoryCleanupResponseDTO):
    """Outcome of DELETE ``/projects/{id}`` (cleanup-shaped)."""

    model_config = model_config()
