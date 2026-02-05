from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel


class StepTagsDTO(BaseModel):
    step: int
    scalar_names: List[str]
    tags: List[str]


class ExperimentsScalarsPointsResultDTO(BaseModel):
    experiment_id: str
    scalars: Dict[str, List[Tuple[int, float]]]
    tags: Optional[List[StepTagsDTO]] = None


class ScalarsPointsResultDTO(BaseModel):
    data: List[ExperimentsScalarsPointsResultDTO]


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


class LogScalarsResponseDTO(BaseModel):
    status: str
