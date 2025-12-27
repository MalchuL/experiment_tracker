from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class ExperimentStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class MetricDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class MetricAggregation(str, Enum):
    LAST = "last"
    BEST = "best"
    AVERAGE = "average"


EXPERIMENT_COLORS = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#ec4899",
    "#06b6d4",
    "#f97316",
    "#84cc16",
    "#6366f1",
]


class ProjectMetric(BaseModel):
    name: str
    direction: MetricDirection
    aggregation: MetricAggregation


class ProjectSettings(BaseModel):
    namingPattern: str = "{num}_from_{parent}_{change}"
    displayMetrics: List[str] = []


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    owner: str = Field(..., min_length=1)
    metrics: List[ProjectMetric] = []
    settings: ProjectSettings = ProjectSettings()


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    owner: Optional[str] = None
    metrics: Optional[List[ProjectMetric]] = None
    settings: Optional[ProjectSettings] = None


class Project(ProjectBase):
    id: str
    createdAt: str
    experimentCount: int = 0
    hypothesisCount: int = 0

    class Config:
        from_attributes = True


class ExperimentBase(BaseModel):
    projectId: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    status: ExperimentStatus = ExperimentStatus.PLANNED
    parentExperimentId: Optional[str] = None
    features: Dict[str, Any] = {}
    gitDiff: Optional[str] = None
    color: Optional[str] = None
    order: Optional[int] = None


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ExperimentStatus] = None
    features: Optional[Dict[str, Any]] = None
    gitDiff: Optional[str] = None
    progress: Optional[int] = None
    order: Optional[int] = None


class Experiment(BaseModel):
    id: str
    projectId: str
    name: str
    description: str
    status: ExperimentStatus
    parentExperimentId: Optional[str]
    rootExperimentId: Optional[str]
    features: Dict[str, Any]
    featuresDiff: Optional[Dict[str, Any]]
    gitDiff: Optional[str]
    progress: int
    color: str
    order: int
    createdAt: str
    startedAt: Optional[str]
    completedAt: Optional[str]

    class Config:
        from_attributes = True


class HypothesisBase(BaseModel):
    projectId: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    author: str = Field(..., min_length=1)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    targetMetrics: List[str] = []
    baseline: str = "root"


class HypothesisCreate(HypothesisBase):
    pass


class HypothesisUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    author: Optional[str] = None
    status: Optional[HypothesisStatus] = None
    targetMetrics: Optional[List[str]] = None
    baseline: Optional[str] = None


class Hypothesis(HypothesisBase):
    id: str
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True


class MetricBase(BaseModel):
    experimentId: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    value: float
    step: int = 0
    direction: MetricDirection = MetricDirection.MINIMIZE


class MetricCreate(MetricBase):
    pass


class Metric(MetricBase):
    id: str
    createdAt: str

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    totalProjects: int
    totalExperiments: int
    runningExperiments: int
    completedExperiments: int
    failedExperiments: int
    totalHypotheses: int
    supportedHypotheses: int
    refutedHypotheses: int


class ExperimentReorder(BaseModel):
    experimentIds: List[str]
