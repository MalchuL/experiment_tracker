from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from typing import Optional, List, Any
from datetime import datetime
from models import MetricDirection, MetricAggregation

from lib.dto_config import model_config
from lib.pagination import PaginatedResponse


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
    owner: ProjectOwnerDTO
    created_at: datetime
    experiment_count: int = 0
    hypothesis_count: int = 0
    team: Optional[ProjectTeamDTO] = None

    model_config = model_config()


class ProjectListResponseDTO(PaginatedResponse[ProjectDTO]):
    model_config = model_config()


class ProjectDataDTO(ProjectBaseDTO):
    id: UUID
    team_id: Optional[UUID] = None
    owner_id: UUID


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
