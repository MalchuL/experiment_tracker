from typing import List, Optional
from uuid import UUID

from experiment_tracker_shared.limits import (
    ENTITY_DESCRIPTION_MAX_LEN,
    ENTITY_NAME_MAX_LEN,
)
from pydantic import BaseModel, Field, field_validator

from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse
from models import HypothesisStatus


class HypothesisBaseDTO(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=ENTITY_NAME_MAX_LEN)
    description: str = Field(default="", max_length=ENTITY_DESCRIPTION_MAX_LEN)
    author: str = Field(..., min_length=1, max_length=ENTITY_NAME_MAX_LEN)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    target_metrics: List[str] = []
    baseline: str = Field(default="root", max_length=ENTITY_NAME_MAX_LEN)

    model_config = model_config()

    @field_validator("target_metrics", mode="after")
    @classmethod
    def validate_target_metric_names(cls, v: List[str]) -> List[str]:
        for i, name in enumerate(v):
            if len(name) > ENTITY_NAME_MAX_LEN:
                raise ValueError(
                    f"target_metrics[{i}] exceeds maximum length "
                    f"({ENTITY_NAME_MAX_LEN} characters)."
                )
        return v


class HypothesisCreateDTO(HypothesisBaseDTO):
    model_config = model_config()


class HypothesisUpdateDTO(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=ENTITY_NAME_MAX_LEN)
    description: Optional[str] = Field(None, max_length=ENTITY_DESCRIPTION_MAX_LEN)
    author: Optional[str] = Field(None, min_length=1, max_length=ENTITY_NAME_MAX_LEN)
    status: Optional[HypothesisStatus] = None
    target_metrics: Optional[List[str]] = None
    baseline: Optional[str] = Field(None, max_length=ENTITY_NAME_MAX_LEN)

    model_config = model_config()

    @field_validator("target_metrics", mode="after")
    @classmethod
    def validate_target_metric_names(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        if v is None:
            return v
        for i, name in enumerate(v):
            if len(name) > ENTITY_NAME_MAX_LEN:
                raise ValueError(
                    f"target_metrics[{i}] exceeds maximum length "
                    f"({ENTITY_NAME_MAX_LEN} characters)."
                )
        return v


class HypothesisDTO(HypothesisBaseDTO):
    id: UUID
    created_at: ApiDateTime
    updated_at: ApiDateTime

    model_config = model_config()


class HypothesisListResponseDTO(PaginatedResponse[HypothesisDTO]):
    model_config = model_config()
