from __future__ import annotations

from pydantic import BaseModel, ConfigDict, RootModel


class CheckProjectArtifactsRequest(RootModel[list[str]]):
    pass


class CheckProjectArtifactsResponse(BaseModel):
    missing: list[str]


class UploadProjectArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None


class DeleteProjectArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None


class DeleteProjectResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None
