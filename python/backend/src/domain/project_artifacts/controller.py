"""Project artifacts controller: get, check, upload, download, snapshots, delete."""

from datetime import datetime
from uuid import UUID

import httpx
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from starlette.responses import Response

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import get_project_artifacts_service
from domain.rbac.permissions import ProjectActions
from models import User

from .dto import ArtifactsResultDTO, LogArtifactResponseDTO, SnapshotCreateRequestDTO
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


def _map_artifacts_to_objects(result: dict) -> dict:
    """Map artifacts_info -> objects and artifact_type -> object_type for frontend."""
    data = result.get("data", [])
    mapped = []
    for item in data:
        mapped_item = dict(item)
        if "artifacts_info" in mapped_item:
            objects = []
            for art in mapped_item.pop("artifacts_info", []):
                obj = dict(art)
                if "artifact_type" in obj:
                    obj["object_type"] = obj.pop("artifact_type")
                objects.append(obj)
            mapped_item["objects"] = objects
        mapped.append(mapped_item)
    return {"data": mapped}


@router.post(
    "/{project_id}/log/{experiment_id}",
    response_model=LogArtifactResponseDTO,
)
async def upload_and_log_artifact(
    project_id: UUID,
    experiment_id: UUID,
    file: UploadFile = File(...),
    name: str = Form(...),
    artifact_type: str = Form(...),
    step: int = Form(...),
    blob_hash: str = Form(..., min_length=64, max_length=64, alias="hash"),
    metadata: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Upload file to project CAS and log artifact metadata in one call."""
    import json

    meta_dict: dict[str, str] | None = None
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="metadata must be valid JSON")

    tags_list: list[str] | None = None
    if tags:
        try:
            tags_list = json.loads(tags)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="tags must be valid JSON array")

    try:
        return await service.upload_and_log_artifact(
            user=user,
            project_id=project_id,
            experiment_id=experiment_id,
            file=file,
            name=name,
            artifact_type=artifact_type,
            step=step,
            blob_hash=blob_hash,
            metadata=meta_dict,
            tags=tags_list,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/{project_id}/get")
async def get_project_artifacts(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    artifact_type: list[str] | None = Query(default=None),
    artifact_name: list[str] | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    format: str | None = Query(default=None, alias="format"),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Get artifacts for a project. Use format=objects for frontend compatibility."""
    try:
        result = await service.get_artifacts(
            user=user,
            project_id=project_id,
            experiment_ids=experiment_id,
            artifact_types=artifact_type,
            artifact_names=artifact_name,
            start_time=start_time,
            end_time=end_time,
        )
        if format == "objects":
            return _map_artifacts_to_objects(result)
        return ArtifactsResultDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post("/{project_id}/check")
async def check_project_blobs(
    project_id: UUID,
    hashes: list[str] = Body(..., embed=False),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Return which content hashes are missing from CAS metadata."""
    try:
        return await service.check_project_blobs(
            user=user, project_id=project_id, hashes=hashes
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post("/{project_id}/upload")
async def upload_project_blob(
    project_id: UUID,
    hash: str = Query(..., min_length=64, max_length=64),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Upload a single blob into CAS storage after hash verification."""
    try:
        return await service.upload_project_blob(
            user=user, project_id=project_id, blob_hash=hash, file=file
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/{project_id}/blobs/{blob_hash}")
async def download_project_blob(
    project_id: UUID,
    blob_hash: str,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Stream a single blob from object storage by content hash."""
    try:
        content = await service.download_project_blob(
            user=user, project_id=project_id, blob_hash=blob_hash
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
):
    """Create a snapshot that links an experiment to existing CAS blobs."""
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
    """Stream a ZIP archive reconstructed from CAS blobs for a snapshot."""
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


@router.delete("/{project_id}/blobs/{blob_hash}")
async def delete_project_blob(
    project_id: UUID,
    blob_hash: str,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Delete one blob from CAS storage and tracked metadata."""
    try:
        return await service.delete_project_blob(
            user=user, project_id=project_id, blob_hash=blob_hash
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_PROJECT)),
    service: ProjectArtifactsServiceProtocol = Depends(get_project_artifacts_service),
):
    """Delete a project and all its blobs and snapshots."""
    try:
        return await service.delete_project(user=user, project_id=project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)
