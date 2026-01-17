from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, List
from models import HypothesisStatus

from lib.dto_config import model_config


class HypothesisBaseDTO(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    author: str = Field(..., min_length=1)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    target_metrics: List[str] = []
    baseline: str = "root"

    model_config = model_config()


class HypothesisCreateDTO(HypothesisBaseDTO):
    pass

    model_config = model_config()


class HypothesisUpdateDTO(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    author: Optional[str] = None
    status: Optional[HypothesisStatus] = None
    target_metrics: Optional[List[str]] = None
    baseline: Optional[str] = None

    model_config = model_config()


class HypothesisDTO(HypothesisBaseDTO):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = model_config()
