from pydantic import BaseModel, Field
from models import MetricDirection


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
