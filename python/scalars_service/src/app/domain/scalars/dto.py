from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.lib.dto_config import model_config


class ScalarsSampling(str, Enum):
    """How scalar rows are subsampled per experiment (see scalars service / ClickHouse query)."""

    UNIFORM = "uniform"


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
    has_next: bool = False
    size: int = 0
    total: int = 0


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


class CompactProjectColumnsResponseDTO(BaseModel):
    model_config = model_config()

    dropped_columns: List[str] = Field(default_factory=list)
