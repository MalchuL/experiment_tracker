from pydantic import BaseModel, Field
from typing import Optional, List
from models import MetricDirection, MetricAggregation


class ProjectMetricDTO(BaseModel):
    name: str
    direction: MetricDirection
    aggregation: MetricAggregation


class ProjectSettingsDTO(BaseModel):
    namingPattern: str = "{num}_from_{parent}_{change}"
    displayMetrics: List[str] = []


class ProjectBaseDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    owner: str = Field(..., min_length=1)
    metrics: List[ProjectMetricDTO] = []
    settings: ProjectSettingsDTO = ProjectSettingsDTO()


class ProjectCreateDTO(ProjectBaseDTO):
    teamId: Optional[str] = None


class ProjectUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    owner: Optional[str] = None
    metrics: Optional[List[ProjectMetricDTO]] = None
    settings: Optional[ProjectSettingsDTO] = None


class ProjectDTO(ProjectBaseDTO):
    id: str
    createdAt: str
    experimentCount: int = 0
    hypothesisCount: int = 0

    class Config:
        from_attributes = True
