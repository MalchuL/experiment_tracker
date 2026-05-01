from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse


@dataclass(frozen=True, slots=True)
class ExperimentArtifactDownloadDTO:
    """Raw bytes plus display metadata for a downloaded experiment artifact (tracked or at-step)."""

    content: bytes
    filename: str
    content_type: str


class ExperimentArtifactDTO(BaseModel):
    id: UUID
    experiment_id: UUID
    name: str
    filepath: str
    filename: str
    mime_type: str
    storage_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: ApiDateTime
    updated_at: ApiDateTime

    model_config = model_config()


class ExperimentArtifactListResponseDTO(PaginatedResponse[ExperimentArtifactDTO]):
    model_config = model_config()


class ExperimentArtifactsDeleteResponseDTO(BaseModel):
    deleted_count: int

    model_config = model_config()
