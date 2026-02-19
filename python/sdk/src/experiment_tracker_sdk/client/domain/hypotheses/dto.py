from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class HypothesisCreateRequest(BaseModel):
    projectId: str
    title: str
    description: str = ""
    author: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    targetMetrics: list[str] = []
    baseline: str = "root"


class HypothesisUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    author: str | None = None
    status: HypothesisStatus | None = None
    targetMetrics: list[str] | None = None
    baseline: str | None = None


class HypothesisResponse(BaseModel):
    id: str
    projectId: str
    title: str
    description: str
    author: str
    status: HypothesisStatus
    targetMetrics: list[str]
    baseline: str
    createdAt: datetime
    updatedAt: datetime


class SuccessResponse(BaseModel):
    success: bool
