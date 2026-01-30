from typing import Optional
from pydantic import BaseModel


class ExperimentCreateRequest(BaseModel):
    projectId: str
    name: str
    description: str = ""


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


class WhoAmIResponse(BaseModel):
    id: str
    email: str
    displayName: Optional[str] = None
