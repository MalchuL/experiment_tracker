from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ObjectType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


class ObjectEntryResponse(BaseModel):
    timestamp: datetime
    step: int
    name: str
    object_type: ObjectType
    path: str
    metadata: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ExperimentObjectsResponse(BaseModel):
    experiment_id: str
    objects: list[ObjectEntryResponse]


class ObjectsPointsResponse(BaseModel):
    data: list[ExperimentObjectsResponse]


class LogObjectRequest(BaseModel):
    name: str
    object_type: ObjectType
    path: str
    step: int
    metadata: dict[str, str] | None = None
    tags: list[str] | None = None

    def model_dump(self, **kwargs: object) -> dict:
        """Serialize for artifacts API (artifact_type instead of object_type)."""
        d = super().model_dump(**kwargs)
        if "object_type" in d:
            d["artifact_type"] = d.pop("object_type")
        return d


class LogObjectResponse(BaseModel):
    status: str
    warnings: list[str] | None = None
