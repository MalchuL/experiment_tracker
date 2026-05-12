from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse


class ProjectReportSummaryDTO(BaseModel):
    """List row without full document payload."""

    id: UUID
    project_id: UUID
    title: str
    created_at: ApiDateTime
    updated_at: ApiDateTime

    model_config = model_config()


class ProjectReportDTO(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    content: dict[str, Any]
    created_at: ApiDateTime
    updated_at: ApiDateTime

    model_config = model_config()


class ProjectReportCreateDTO(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    content: Optional[dict[str, Any]] = None

    model_config = model_config()


class ProjectReportUpdateDTO(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[dict[str, Any]] = None

    model_config = model_config()


class ProjectReportListResponseDTO(PaginatedResponse[ProjectReportSummaryDTO]):
    model_config = model_config()
