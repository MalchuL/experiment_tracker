from datetime import datetime
import re
from uuid import UUID
from lib.types import UUID_TYPE
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from models import ExperimentStatus

from lib.dto_config import model_config


class ExperimentBaseDTO(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    status: ExperimentStatus = ExperimentStatus.PLANNED
    parent_experiment_id: Optional[UUID_TYPE] = None
    features: Dict[str, Any] = {}
    git_diff: Optional[str] = None
    color: Optional[str] = None
    order: Optional[int] = None

    model_config = model_config()

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("Invalid color")
        return v


class ExperimentCreateDTO(ExperimentBaseDTO):
    model_config = model_config()


class ExperimentUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    parent_experiment_id: Optional[UUID_TYPE] = None
    color: Optional[str] = None
    status: Optional[ExperimentStatus] = None
    features: Optional[Dict[str, Any]] = None
    git_diff: Optional[str] = None
    progress: Optional[int] = None
    order: Optional[int] = None

    model_config = model_config()


class ExperimentDTO(ExperimentBaseDTO):
    id: UUID
    features_diff: Optional[Dict[str, Any]]
    progress: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = model_config()


class ExperimentReorderDTO(BaseModel):
    project_id: UUID
    experiment_ids: List[UUID]

    model_config = model_config()
