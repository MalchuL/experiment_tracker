from __future__ import annotations

from pydantic import BaseModel, ConfigDict, RootModel


class CheckProjectArtifactsRequest(RootModel[list[str]]):
    pass


class CheckProjectArtifactsResponse(BaseModel):
    missing: list[str]


class UploadProjectArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None


class SnapshotFileEntry(BaseModel):
    """Project snapshot manifest entry for object-storage APIs.

    Args:
        path: Relative file path stored in the ZIP snapshot.
        hash: Content-addressed project artifact hash for that file.

    Result:
        Validated file entry embedded in snapshot creation requests.
    """

    path: str
    hash: str


class SnapshotCreateRequest(BaseModel):
    """Request body for creating a project-scoped snapshot archive.

    Args:
        project_id: Project that owns the content-addressed blobs.
        experiment_id: Experiment whose file snapshot is being archived.
        files: Ordered manifest entries to include in the archive.

    Result:
        Payload sent to object storage to create a ZIP snapshot from project
        artifacts.
    """

    project_id: str
    experiment_id: str
    files: list[SnapshotFileEntry]


class SnapshotCreateResponse(BaseModel):
    """Response returned after object storage creates a snapshot archive.

    Args:
        snapshot_id: UUID-like identifier for the stored snapshot archive.

    Result:
        Parsed creation response with unknown service fields preserved.
    """

    model_config = ConfigDict(extra="allow")

    snapshot_id: str


class DeleteProjectArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None


class DeleteProjectResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None
