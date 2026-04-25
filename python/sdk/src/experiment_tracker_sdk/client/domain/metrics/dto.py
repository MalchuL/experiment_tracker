from datetime import datetime
from pydantic import BaseModel

from ...pagination import PaginatedResponse


class MetricCreateRequest(BaseModel):
    experimentId: str
    name: str
    value: float
    step: int = 0
    label: str | None = None


class MetricResponse(BaseModel):
    id: str
    experimentId: str
    name: str
    value: float
    step: int
    label: str | None = None
    createdAt: datetime


class MetricListResponse(PaginatedResponse[MetricResponse]):
    pass
