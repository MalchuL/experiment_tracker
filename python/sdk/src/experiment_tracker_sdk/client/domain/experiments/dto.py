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
    tags: Optional[list[str]] = None


class ExperimentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    parentExperimentId: Optional[str | UUID] = None
    features: Optional[dict[str, Any]] = None
    gitDiff: Optional[str] = None
    status: Optional[ExperimentStatus] = None
    progress: Optional[int] = None
    tags: Optional[list[str]] = None


class ExperimentResponse(BaseModel):
    id: str
    projectId: str
    name: str
    description: str
    status: str
    color: Optional[str] = None
    tags: Optional[list[str]] = None
    parentExperimentId: Optional[str | UUID] = None
    features: Optional[dict[str, Any]] = None
    gitDiff: Optional[str] = None
    progress: Optional[int] = None
    createdAt: datetime
    startedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None


class SuccessResponse(BaseModel):
    success: bool
