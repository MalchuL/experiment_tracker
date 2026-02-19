from datetime import datetime
from enum import Enum
from pydantic import BaseModel


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


class ProjectSettingsResponse(BaseModel):
    namingPattern: str
    displayMetrics: list[str] = []


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    metrics: list[ProjectMetricResponse] = []
    settings: ProjectSettingsResponse | None = None
    teamId: str | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    metrics: list[ProjectMetricResponse] | None = None
    settings: ProjectSettingsResponse | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    metrics: list[ProjectMetricResponse]
    settings: ProjectSettingsResponse
    owner: ProjectOwnerResponse
    createdAt: datetime
    experimentCount: int = 0
    hypothesisCount: int = 0
    team: ProjectTeamResponse | None = None


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
