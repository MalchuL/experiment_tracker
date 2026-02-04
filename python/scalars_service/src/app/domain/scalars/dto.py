from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ExperimentsScalarsPointsResultDTO(BaseModel):
    experiment_id: str
    scalars: List[Tuple[int, float]]
    tags: Optional[List[Tuple[int, List[str]]]] = None


class ScalarsPointsResultDTO(BaseModel):
    data: List[ExperimentsScalarsPointsResultDTO]
    tags: List[str]


class LogScalarRequestDTO(BaseModel):
    """Request DTO for logging a single scalar"""

    scalar_name: str
    value: float
    step: Optional[int] = None
    tags: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
