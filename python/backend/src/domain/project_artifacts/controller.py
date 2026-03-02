"""Project artifacts controller: check, upload, download, snapshots, delete."""

from uuid import UUID

import httpx
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from starlette.responses import Response

from clients.object_storage import (
    CheckProjectArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadProjectArtifactResponseDTO,
)
from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import get_project_artifacts_service
from domain.rbac.permissions import ProjectActions
from models import User

from .error import ProjectArtifactsNotAccessibleError
from .service import ProjectArtifactsServiceProtocol

router = APIRouter(prefix="/project-artifacts", tags=["project-artifacts"])


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, ProjectArtifactsNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=error.response.status_code,
            detail=error.response.text,
        )
    if isinstance(error, httpx.RequestError):
        raise HTTPException(
            status_code=502,
            detail="Project artifacts service unavailable",
        )
    raise HTTPException(status_code=400, detail=str(error))


@router.post("/{project_id}/check")
async def check_project_artifacts(
    project_id: UUID,
    hashes: list[str] = Body(..., embed=False),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
) -> CheckProjectArtifactsResponseDTO:
    """Return which content hashes are missing from CAS metadata."""
    try:
        return await service.check_project_artifacts(
            user=user, project_id=project_id, hashes=hashes
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post("/{project_id}/upload")
async def upload_project_artifact(
    project_id: UUID,
    hash: str = Query(..., min_length=64, max_length=64),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
) -> UploadProjectArtifactResponseDTO:
    """Upload a single artifact into CAS storage after hash verification."""
    try:
        return await service.upload_project_artifact(
            user=user, project_id=project_id, artifact_hash=hash, file=file
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/{project_id}/artifacts/{artifact_hash}")
async def download_project_artifact(
    project_id: UUID,
    artifact_hash: str,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Stream a single artifact from object storage by content hash."""
    try:
        content = await service.download_project_artifact(
            user=user, project_id=project_id, artifact_hash=artifact_hash
        )
        return Response(
            content=content,
            media_type="application/octet-stream",
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post("/{project_id}/snapshots")
async def create_project_snapshot(
    project_id: UUID,
    payload: SnapshotCreateRequestDTO = Body(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
) -> SnapshotCreateResponseDTO:
    """Create a snapshot that links an experiment to existing CAS artifacts."""
    try:
        return await service.create_project_snapshot(
            user=user, project_id=project_id, payload=payload
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/{project_id}/snapshots/{snapshot_id}/download")
async def download_project_snapshot(
    project_id: UUID,
    snapshot_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Stream a ZIP archive reconstructed from CAS artifacts for a snapshot."""
    try:
        content = await service.download_project_snapshot(
            user=user, project_id=project_id, snapshot_id=snapshot_id
        )
        return Response(
            content=content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="snapshot-{snapshot_id}.zip"'
            },
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/{project_id}/artifacts/{artifact_hash}")
async def delete_project_artifact(
    project_id: UUID,
    artifact_hash: str,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
) -> DeleteProjectArtifactResponseDTO:
    """Delete one artifact from CAS storage and tracked metadata."""
    try:
        return await service.delete_project_artifact(
            user=user, project_id=project_id, artifact_hash=artifact_hash
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_PROJECT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
) -> DeleteProjectResponseDTO:
    """Delete a project and all its artifacts and snapshots."""
    try:
        return await service.delete_project(user=user, project_id=project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)
