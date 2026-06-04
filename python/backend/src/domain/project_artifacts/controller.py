"""Project artifacts controller: check, upload, download, snapshots, delete."""

from uuid import UUID

import httpx
from experiment_tracker_shared import compute_sha256_hexdigest
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
from .protocol import ProjectArtifactsServiceProtocol

router = APIRouter(prefix="/project-artifacts", tags=["project-artifacts"])


def _raise_http_error(error: Exception) -> None:
    """Translate project-artifact service/client errors into HTTP responses.

    Args:
        error: Exception raised by the project-artifact service or object-storage
            HTTP client.

    Raises:
        HTTPException: ``403`` for access denial, upstream status codes for
            ``httpx.HTTPStatusError``, ``502`` when object storage is unreachable, and
            ``400`` for other errors.
    """
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


def _snapshot_download_response(
    response: httpx.Response, fallback_filename: str
) -> Response:
    """Map an upstream snapshot ZIP response to the public backend response."""

    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "application/zip"),
        headers={
            "Content-Disposition": response.headers.get(
                "content-disposition",
                f'attachment; filename="{fallback_filename}"',
            )
        },
    )


@router.post("/{project_id}/check")
async def check_project_artifacts(
    project_id: UUID,
    hashes: list[str] = Body(..., embed=False),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
) -> CheckProjectArtifactsResponseDTO:
    """Return which content hashes are missing from project CAS metadata.

    Args:
        project_id: Project whose CAS namespace should be checked.
        hashes: Content hashes to test for existence.
        user: Authenticated user performing the check before upload.
        _: API-token scope guard requiring artifact logging access.
        service: Project-artifacts service dependency.

    Returns:
        CheckProjectArtifactsResponseDTO: Hashes that are absent and need upload.

    Raises:
        HTTPException: ``403`` for insufficient project artifact permission, ``502``
            for object-storage connectivity failures, upstream status codes for
            object-storage HTTP errors, and ``400`` for other service errors.
    """
    try:
        return await service.check_project_artifacts(
            user=user, project_id=project_id, hashes=hashes
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post("/{project_id}/upload")
async def upload_project_artifact(
    project_id: UUID,
    hash: str | None = Query(default=None, min_length=64, max_length=64),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
) -> UploadProjectArtifactResponseDTO:
    """Upload one content-addressed project artifact.

    Args:
        project_id: Project whose CAS namespace receives the artifact.
        hash: Expected SHA-256 content hash supplied as the logical key.
        file: Multipart file stream to store.
        user: Authenticated user performing the upload.
        _: API-token scope guard requiring artifact logging access.
        service: Project-artifacts service dependency.

    Returns:
        UploadProjectArtifactResponseDTO: Object-storage upload result.

    Raises:
        HTTPException: ``403`` for insufficient permission, ``502`` for storage
            unavailability, upstream HTTP status codes, or ``400`` for other errors.
    """
    try:
        if hash is None:
            content = await file.read()
            hash = compute_sha256_hexdigest(content)
            await file.seek(0)
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
    """Download one project artifact by content hash.

    Args:
        project_id: Project whose CAS namespace contains the artifact.
        artifact_hash: Content hash to download.
        user: Authenticated user requesting bytes.
        _: API-token scope guard requiring artifact view access.
        service: Project-artifacts service dependency.

    Returns:
        Response: Binary ``application/octet-stream`` payload.

    Raises:
        HTTPException: ``403`` for insufficient permission, ``502`` for storage
            unavailability, upstream HTTP status codes, or ``400`` for other errors.
    """
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
    """Create a project snapshot from existing CAS artifacts.

    Args:
        project_id: Project that owns the snapshot.
        payload: Snapshot metadata and artifact references.
        user: Authenticated user creating the snapshot.
        _: API-token scope guard requiring artifact logging access.
        service: Project-artifacts service dependency.

    Returns:
        SnapshotCreateResponseDTO: Snapshot identifier and storage result metadata.

    Raises:
        HTTPException: ``403`` for insufficient permission, ``502`` for storage
            unavailability, upstream HTTP status codes, or ``400`` for other errors.
    """
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
    """Download one project snapshot as a ZIP archive."""
    try:
        response = await service.download_project_snapshot(
            user=user, project_id=project_id, snapshot_id=snapshot_id
        )
        return _snapshot_download_response(response, f"snapshot-{snapshot_id}.zip")
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
    """Delete one project CAS artifact and its metadata.

    Args:
        project_id: Project whose artifact should be removed.
        artifact_hash: Content hash to delete.
        user: Authenticated user performing the delete.
        _: API-token scope guard requiring artifact logging access.
        service: Project-artifacts service dependency.

    Returns:
        DeleteProjectArtifactResponseDTO: Storage-service deletion result.

    Raises:
        HTTPException: ``403`` for insufficient permission, ``502`` for storage
            unavailability, upstream HTTP status codes, or ``400`` for other errors.
    """
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
    """Delete all object-storage data for a project.

    Args:
        project_id: Project whose artifacts and snapshots should be removed.
        user: Authenticated user performing the project artifact cleanup.
        _: API-token scope guard requiring project delete access.
        service: Project-artifacts service dependency.

    Returns:
        DeleteProjectResponseDTO: Storage-service project deletion result.

    Raises:
        HTTPException: ``403`` for insufficient permission, ``502`` for storage
            unavailability, upstream HTTP status codes, or ``400`` for other errors.
    """
    try:
        return await service.delete_project(user=user, project_id=project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)
