from uuid import UUID
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime


class StepTagsDTO(BaseModel):
    step: int
    scalar_names: List[str]
    tags: List[str]


class ScalarSeriesDTO(BaseModel):
    x: List[int]
    y: List[float]


class ExperimentsScalarsPointsResultDTO(BaseModel):
    experiment_id: UUID
    scalars: Dict[str, ScalarSeriesDTO]  # scalar name -> scalar series
    tags: Optional[List[StepTagsDTO]] = None


class ScalarsPointsResultDTO(BaseModel):
    data: List[ExperimentsScalarsPointsResultDTO]


class LastLoggedExperimentsRequestDTO(BaseModel):
    experiment_ids: List[UUID] | None = None


class LastLoggedExperimentDTO(BaseModel):
    experiment_id: UUID
    last_modified: datetime


class LastLoggedExperimentsResultDTO(BaseModel):
    data: List[LastLoggedExperimentDTO]


class LogScalarRequestDTO(BaseModel):
    """Request DTO for logging multiple scalars at a single step"""

    scalars: Dict[str, float]
    step: int
    tags: List[str] | None = None


class LogScalarsRequestDTO(BaseModel):
    """Request DTO for logging multiple scalars"""

    scalars: List[LogScalarRequestDTO]


class LogScalarResponseDTO(BaseModel):
    status: str
    warnings: List[str] | None = None


class LogScalarsResponseDTO(BaseModel):
    status: str
    warnings: List[str] | None = None
