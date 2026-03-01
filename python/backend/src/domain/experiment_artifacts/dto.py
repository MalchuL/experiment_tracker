from typing import Literal

from pydantic import BaseModel

ArtifactType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


class LogArtifactResponseDTO(BaseModel):
    status: str
    warnings: list[str] | None = None


class LogArtifactRequestDTO(BaseModel):
    name: str
    artifact_type: ArtifactType
    path: str
    step: int
    metadata: dict[str, str] | None = None
    tags: list[str] | None = None
