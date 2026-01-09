from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from models import ExperimentStatus


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
    color: Optional[str] = None
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


class ExperimentReorder(BaseModel):
    experimentIds: List[str]
