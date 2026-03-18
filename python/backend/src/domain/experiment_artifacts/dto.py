from __future__ import annotations

from datetime import datetime
from uuid import UUID

from lib.dto_config import model_config
from pydantic import BaseModel


class ExperimentArtifactDTO(BaseModel):
    id: UUID
    experiment_id: UUID
    name: str
    filepath: str
    filename: str
    mime_type: str
    storage_path: str
    created_at: datetime
    updated_at: datetime

    model_config = model_config()


class ExperimentArtifactsDeleteResponseDTO(BaseModel):
    deleted_count: int

    model_config = model_config()
