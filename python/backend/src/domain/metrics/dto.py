from datetime import datetime
from pydantic import BaseModel, Field
from models import MetricDirection

from lib.dto_config import model_config
from lib.types import UUID_TYPE


class MetricBase(BaseModel):
    experiment_id: UUID_TYPE
    name: str = Field(..., min_length=1)
    value: float
    step: int = 0
    direction: MetricDirection = MetricDirection.MAXIMIZE

    model_config = model_config()


class MetricCreate(MetricBase):
    pass

    model_config = model_config()


class Metric(MetricBase):
    id: UUID_TYPE
    created_at: datetime

    model_config = model_config()


class MetricUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    value: float | None = None
    step: int | None = None
    direction: MetricDirection | None = None

    model_config = model_config()
