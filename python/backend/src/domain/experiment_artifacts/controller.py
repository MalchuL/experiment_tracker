"""Experiment artifacts controller: log, upload, download, delete."""

import json
from datetime import datetime
from uuid import UUID

from clients.artifacts_info import (
    ArtifactsInfoResultDTO,
    LogArtifactResponseDTO as ArtifactsInfoLogArtifactResponseDTO,
)
from clients.object_storage import (
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
)
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from starlette.background import BackgroundTask
from starlette.responses import Response, StreamingResponse

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import get_experiment_artifacts_service
from domain.rbac.permissions import ProjectActions
from models import User

from .dto import (
    ExperimentArtifactDTO,
    ExperimentArtifactsDeleteResponseDTO,
)
from .error import (
    ExperimentArtifactsNotAccessibleError,
    ExperimentArtifactNotFoundError,
)
from .service import ExperimentArtifactsServiceProtocol

router = APIRouter(prefix="/experiment-artifacts", tags=["experiment-artifacts"])


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, ExperimentArtifactsNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, ExperimentArtifactNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=error.response.status_code,
            detail=error.response.text,
        )
    if isinstance(error, httpx.RequestError):
        raise HTTPException(
            status_code=502,
            detail="Experiment artifacts service unavailable",
        )
    raise HTTPException(status_code=400, detail=str(error))


@router.get("/experiments/{experiment_id}", response_model=list[ExperimentArtifactDTO])
async def list_experiment_artifacts(
    experiment_id: UUID,
    name: list[str] | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> list[ExperimentArtifactDTO]:
    """List named artifacts for one experiment."""
    try:
        return await service.list_experiment_artifacts(
            user=user,
            experiment_id=experiment_id,
            names=name,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/projects/{project_id}/get-at-step")
async def get_project_artifacts_at_step(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    artifact_type: list[str] | None = Query(default=None),
    artifact_name: list[str] | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ArtifactsInfoResultDTO:
    """List project artifacts using experiment-artifacts domain."""
    try:
        result = await service.get_project_artifacts_at_step(
            user=user,
            project_id=project_id,
            experiment_ids=experiment_id,
            artifact_types=artifact_type,
            artifact_names=artifact_name,
            start_time=start_time.isoformat() if start_time else None,
            end_time=end_time.isoformat() if end_time else None,
        )
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post(
    "/{experiment_id}/log-at-step",
    response_model=ArtifactsInfoLogArtifactResponseDTO,
)
async def upload_and_log_experiment_artifact_at_step(
    experiment_id: UUID,
    file: UploadFile = File(...),
    name: str = Form(...),
    artifact_type: str = Form(...),
    step: int = Form(...),
    metadata: str | None = Form(None),
    tags: str | None = Form(None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ArtifactsInfoLogArtifactResponseDTO:
    """Upload file to experiment bucket and log metadata to scalars."""
    metadata_dict: dict[str, str] | None = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            metadata_dict = {"raw": metadata}
    tags_list: list[str] | None = None
    if tags:
        try:
            tags_list = json.loads(tags)
        except json.JSONDecodeError:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    try:
        return await service.upload_and_log_experiment_artifact_at_step(
            user=user,
            experiment_id=experiment_id,
            file=file,
            name=name,
            artifact_type=artifact_type,
            step=step,
            metadata=metadata_dict,
            tags=tags_list,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/{experiment_id}/download-at-step")
async def download_experiment_artifact_at_step(
    experiment_id: UUID,
    path: str = Query(..., min_length=1),
    media_type: str | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
):
    """Download artifact by path from experiment bucket."""
    try:
        content = await service.download_experiment_artifact_at_step(
            user=user, experiment_id=experiment_id, path=path
        )
        return Response(
            content=content,
            media_type=media_type or "application/octet-stream",
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/{experiment_id}/at-step")
async def delete_experiment_artifact_at_step(
    experiment_id: UUID,
    path: str = Query(..., min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> DeleteExperimentArtifactResponseDTO:
    """Delete one artifact by path from experiment bucket."""
    try:
        result = await service.delete_experiment_artifact_at_step(
            user=user, experiment_id=experiment_id, path=path
        )
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/{experiment_id}/at-step")
async def delete_all_experiment_artifacts_at_step(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> DeleteExperimentArtifactsResponseDTO:
    """Delete all artifacts for an experiment."""
    try:
        result = await service.delete_experiment_artifacts_at_step(
            user=user, experiment_id=experiment_id
        )
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post("/upsert", response_model=ExperimentArtifactDTO)
async def upsert_experiment_artifact(
    experiment_id: UUID = Form(...),
    name: str = Form(...),
    filepath: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ExperimentArtifactDTO:
    """Upsert one artifact metadata row and object payload."""
    try:
        return await service.upsert_experiment_artifact(
            user=user,
            experiment_id=experiment_id,
            name=name,
            filepath=filepath,
            file=file,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/get", response_model=ExperimentArtifactDTO)
async def get_experiment_artifact(
    experiment_id: UUID,
    name: str = Query(..., min_length=1),
    filepath: str = Query(..., min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ExperimentArtifactDTO:
    """Get one artifact metadata row."""
    try:
        return await service.get_experiment_artifact(
            user=user,
            experiment_id=experiment_id,
            name=name,
            filepath=filepath,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/download")
async def download_experiment_artifact(
    experiment_id: UUID,
    name: str = Query(..., min_length=1),
    filepath: str = Query(..., min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
):
    """Download one artifact by experiment/name/filepath."""
    try:
        content, mime_type, filename = await service.download_experiment_artifact(
            user=user,
            experiment_id=experiment_id,
            name=name,
            filepath=filepath,
        )
        return Response(
            content=content,
            media_type=mime_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/download/archive")
async def download_experiment_artifacts_archive(
    experiment_id: UUID,
    name: str = Query(..., min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
):
    """Download all artifacts with same name as ZIP."""
    try:
        archive_path, filename = await service.download_experiment_artifacts_archive(
            user=user,
            experiment_id=experiment_id,
            name=name,
        )

        def _cleanup() -> None:
            import os

            if os.path.exists(archive_path):
                os.remove(archive_path)

        return StreamingResponse(
            open(archive_path, "rb"),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            background=BackgroundTask(_cleanup),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/delete", response_model=ExperimentArtifactsDeleteResponseDTO)
async def delete_experiment_artifacts(
    experiment_id: UUID,
    name: str = Query(..., min_length=1),
    filepath: str | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ExperimentArtifactsDeleteResponseDTO:
    """Delete artifacts by name or by name+filepath."""
    try:
        return await service.delete_experiment_artifacts(
            user=user,
            experiment_id=experiment_id,
            name=name,
            filepath=filepath,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)
