from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator

from ...pagination import PaginatedResponse

class MetricDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class MetricAggregation(str, Enum):
    LAST = "last"
    BEST = "best"
    AVERAGE = "average"


class ProjectOwnerResponse(BaseModel):
    id: str
    email: str | None = None
    displayName: str | None = None


class ProjectTeamResponse(BaseModel):
    id: str
    name: str | None = None


class ProjectMetricResponse(BaseModel):
    name: str
    direction: MetricDirection
    aggregation: MetricAggregation
    label: str | None = None


class ProjectDisplayMetricKeyResponse(BaseModel):
    """Subset of a tracked metric used in project `displayMetrics` (API camelCase keys)."""

    name: str
    label: str | None = None


class ProjectMetricsResponse(BaseModel):
    trackedMetrics: list[ProjectMetricResponse] = []
    displayMetrics: list[ProjectDisplayMetricKeyResponse] = []

    @field_validator("displayMetrics", mode="before")
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


class ProjectSettingResponse(BaseModel):
    name: str
    description: str = ""
    type: ProjectSettingType
    value: object | None = None


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    metrics: ProjectMetricsResponse = ProjectMetricsResponse()
    settings: list[ProjectSettingResponse] = []
    teamId: str | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    metrics: ProjectMetricsResponse | None = None
    settings: list[ProjectSettingResponse] | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    metrics: ProjectMetricsResponse
    settings: list[ProjectSettingResponse]
    owner: ProjectOwnerResponse
    createdAt: datetime
    experimentCount: int = 0
    hypothesisCount: int = 0
    team: ProjectTeamResponse | None = None


class ProjectListResponse(PaginatedResponse[ProjectResponse]):
    pass


class DashboardStatsResponse(BaseModel):
    totalExperiments: int
    runningExperiments: int
    completedExperiments: int
    failedExperiments: int
    totalHypotheses: int
    supportedHypotheses: int
    refutedHypotheses: int


class SuccessResponse(BaseModel):
    success: bool
