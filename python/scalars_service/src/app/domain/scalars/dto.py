from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ExperimentsScalarsPointsResultDTO(BaseModel):
    experiment_id: str
    scalars: Dict[str, List[Tuple[int, float]]]
    tags: Optional[Dict[str, List[Tuple[int, List[str]]]]] = None


class ScalarsPointsResultDTO(BaseModel):
    data: List[ExperimentsScalarsPointsResultDTO]


class LogScalarRequestDTO(BaseModel):
    """Request DTO for logging a single scalar"""

    scalar_name: str
    value: float
    step: int
    tags: List[str] | None = None


class LogScalarsRequestDTO(BaseModel):
    """Request DTO for logging multiple scalars"""

    scalars: List[LogScalarRequestDTO]


class LogScalarResponseDTO(BaseModel):
    status: str


class LogScalarsResponseDTO(BaseModel):
    status: str
