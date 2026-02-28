from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LastLoggedExperimentsRequestDTO(BaseModel):
    experiment_ids: list[UUID] | None = None


class LastLoggedExperimentDTO(BaseModel):
    experiment_id: UUID
    last_modified: str  # ISO format string for JSON serialization


class LastLoggedExperimentsResultDTO(BaseModel):
    data: list[LastLoggedExperimentDTO]
