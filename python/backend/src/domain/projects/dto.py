from uuid import UUID
from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel, to_snake

from typing import Optional, List, Any
from datetime import datetime
from models import MetricDirection, MetricAggregation


model_config = ConfigDict(
    alias_generator=AliasGenerator(
        validation_alias=to_camel,  # Input: FirstName -> first_name
        serialization_alias=to_camel,  # Output: first_name -> firstName
    ),
    extra="forbid",
    populate_by_name=True,
)


class ProjectOwnerDTO(BaseModel):
    id: UUID
    email: Optional[str] = None
    display_name: Optional[str] = None

    model_config = model_config


class ProjectTeamDTO(BaseModel):
    id: UUID
    name: Optional[str] = None

    model_config = model_config


class ProjectMetricDTO(BaseModel):
    name: str
    direction: MetricDirection
    aggregation: MetricAggregation

    model_config = model_config


class ProjectSettingsDTO(BaseModel):
    naming_pattern: str = "{num}_from_{parent}_{change}"
    display_metrics: List[str] = []

    model_config = model_config


class ProjectBaseDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    metrics: List[ProjectMetricDTO] = []
    settings: ProjectSettingsDTO = ProjectSettingsDTO()

    model_config = model_config


class ProjectDTO(ProjectBaseDTO):
    id: UUID
    owner: ProjectOwnerDTO
    created_at: datetime
    experiment_count: int = 0
    hypothesis_count: int = 0
    team: Optional[ProjectTeamDTO] = None

    model_config = model_config


class ProjectUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    metrics: Optional[List[ProjectMetricDTO]] = None
    settings: Optional[ProjectSettingsDTO] = None

    model_config = model_config


class ProjectCreateDTO(ProjectBaseDTO):
    team_id: Optional[UUID] = None

    model_config = model_config
