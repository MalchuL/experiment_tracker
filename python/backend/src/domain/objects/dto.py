from datetime import datetime
from typing import Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ObjectType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


class ObjectEntryDTO(BaseModel):
    timestamp: datetime
    step: int
    name: str
    object_type: ObjectType
    path: str
    metadata: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class ExperimentObjectsResultDTO(BaseModel):
    experiment_id: UUID
    objects: List[ObjectEntryDTO]


class ObjectsResultDTO(BaseModel):
    data: List[ExperimentObjectsResultDTO]


class LogObjectRequestDTO(BaseModel):
    name: str
    object_type: ObjectType
    path: str
    step: int
    metadata: Dict[str, str] | None = None
    tags: List[str] | None = None


class LogObjectsRequestDTO(BaseModel):
    objects: List[LogObjectRequestDTO]


class LogObjectResponseDTO(BaseModel):
    status: str
    warnings: List[str] | None = None


class LogObjectsResponseDTO(BaseModel):
    status: str
    warnings: List[str] | None = None
