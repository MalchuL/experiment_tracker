from datetime import datetime
from pydantic import BaseModel

from ...pagination import PaginatedResponse


class MetricUpsertRequest(BaseModel):
    experimentId: str
    name: str
    value: float
    label: str | None = None


class MetricResponse(BaseModel):
    id: str
    experimentId: str
    name: str
    value: float
    label: str | None = None
    createdAt: datetime


class MetricListResponse(PaginatedResponse[MetricResponse]):
    pass


class MetricLabelsResponse(BaseModel):
    labels: list[str] = []
    hasUnlabeled: bool = False


class UniqueMetricDimensionItem(BaseModel):
    name: str
    label: str | None = None


class UniqueMetricDimensionsResponse(BaseModel):
    items: list[UniqueMetricDimensionItem] = []


class MetricsByLabelRowResponse(BaseModel):
    experimentId: str
    experimentName: str
    createdAt: datetime
    color: str
    values: list[float | None]


class MetricsByLabelSnapshotResponse(BaseModel):
    metricNames: list[str] = []
    rows: list[MetricsByLabelRowResponse] = []
    hasNext: bool = False
    total: int = 0
