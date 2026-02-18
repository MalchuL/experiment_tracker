from datetime import datetime
from typing import Dict
from pydantic import BaseModel, Field
from models import MetricDirection

from lib.dto_config import model_config
from lib.types import UUID_TYPE


class MetricBase(BaseModel):
    experiment_id: UUID_TYPE
    name: str = Field(..., min_length=1)
    value: float
    step: int = 0
    label: str | None = None
    model_config = model_config()


class MetricCreateDTO(MetricBase):
    pass

    model_config = model_config()


class MetricDTO(MetricBase):
    id: UUID_TYPE
    created_at: datetime

    model_config = model_config()


class MetricUpdateDTO(BaseModel):
    name: str | None = Field(None, min_length=1)
    value: float | None = None
    step: int | None = None
    label: str | None = None

    model_config = model_config()
