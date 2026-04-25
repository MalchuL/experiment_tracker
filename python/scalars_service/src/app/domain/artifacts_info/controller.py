from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.service_dependencies import get_artifacts_info_service
from .dto import (
    LogArtifactInfoRequestDTO,
    LogArtifactInfoResponseDTO,
    LogArtifactsInfoRequestDTO,
    LogArtifactsInfoResponseDTO,
    ArtifactsInfoResultDTO,
)
from .service import ArtifactsInfoService

router = APIRouter(prefix="/artifacts_info", tags=["artifacts_info"])


@router.post(
    "/log/{project_id}/{experiment_id}", response_model=LogArtifactInfoResponseDTO
)
async def log_artifact_info(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogArtifactInfoRequestDTO,
    service: ArtifactsInfoService = Depends(get_artifacts_info_service),
):
    return await service.log_artifact_info(project_id, experiment_id, payload)


@router.post(
    "/log_batch/{project_id}/{experiment_id}",
    response_model=LogArtifactsInfoResponseDTO,
)
async def log_artifact_info_batch(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogArtifactsInfoRequestDTO,
    service: ArtifactsInfoService = Depends(get_artifacts_info_service),
):
    return await service.log_artifact_info_batch(project_id, experiment_id, payload)


@router.get("/get/{project_id}", response_model=ArtifactsInfoResultDTO)
async def get_artifact_info(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    artifact_type: list[str] | None = Query(default=None),
    artifact_name: list[str] | None = Query(default=None),
    step: list[int] | None = Query(default=None),
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    service: ArtifactsInfoService = Depends(get_artifacts_info_service),
):
    return await service.get_artifacts_info(
        project_id=project_id,
        experiment_id=experiment_id,
        artifact_types=artifact_type,
        artifact_names=artifact_name,
        steps=step,
        limit=limit,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
    )
