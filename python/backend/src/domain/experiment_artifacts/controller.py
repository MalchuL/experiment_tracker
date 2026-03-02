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
from starlette.responses import Response

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import get_experiment_artifacts_service
from domain.rbac.permissions import ProjectActions
from models import User

from .error import ExperimentArtifactsNotAccessibleError
from .service import ExperimentArtifactsServiceProtocol

router = APIRouter(prefix="/experiment-artifacts", tags=["experiment-artifacts"])


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, ExperimentArtifactsNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
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


@router.get("/projects/{project_id}/get")
async def get_project_artifacts(
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
        result = await service.get_project_artifacts(
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
    "/{experiment_id}/log",
    response_model=ArtifactsInfoLogArtifactResponseDTO,
)
async def upload_and_log_experiment_artifact(
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
        return await service.upload_and_log_experiment_artifact(
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


@router.get("/{experiment_id}/download")
async def download_experiment_artifact(
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
        content = await service.download_experiment_artifact(
            user=user, experiment_id=experiment_id, path=path
        )
        return Response(
            content=content,
            media_type=media_type or "application/octet-stream",
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/{experiment_id}")
async def delete_experiment_artifact(
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
        result = await service.delete_experiment_artifact(
            user=user, experiment_id=experiment_id, path=path
        )
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/experiments/{experiment_id}")
async def delete_all_experiment_artifacts(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> DeleteExperimentArtifactsResponseDTO:
    """Delete all artifacts for an experiment."""
    try:
        result = await service.delete_experiment_artifacts(
            user=user, experiment_id=experiment_id
        )
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)
