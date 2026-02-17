from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel


class ExperimentStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ExperimentCreateRequest(BaseModel):
    projectId: str | UUID
    name: str
    description: str = ""
    color: Optional[str] = None
    parentExperimentId: Optional[str | UUID] = None
    features: Optional[dict[str, Any]] = None
    gitDiff: Optional[str] = None
    status: ExperimentStatus = ExperimentStatus.PLANNED


class ExperimentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    parentExperimentId: Optional[str | UUID] = None
    features: Optional[dict[str, Any]] = None
    gitDiff: Optional[str] = None
    status: Optional[ExperimentStatus] = None
    progress: Optional[int] = None


class ExperimentResponse(BaseModel):
    id: str
    projectId: str
    name: str
    description: str
    status: str


class MetricCreateRequest(BaseModel):
    experimentId: str
    name: str
    value: float
    step: int = 0
    direction: str = "maximize"


class ScalarLogRequest(BaseModel):
    scalars: dict[str, float]
    step: int = 0
    tags: list[str] | None = None


class LastLoggedExperimentsRequest(BaseModel):
    experiment_ids: list[str] | None = None


class LastLoggedExperiment(BaseModel):
    experiment_id: str
    last_modified: datetime


class LastLoggedExperimentsResponse(BaseModel):
    data: list[LastLoggedExperiment]


class WhoAmIResponse(BaseModel):
    id: str
    email: str
    displayName: Optional[str] = None
