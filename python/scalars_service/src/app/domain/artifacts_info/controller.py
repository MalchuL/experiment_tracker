from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.service_dependencies import get_artifacts_info_service
from .dto import (
    LogArtifactInfoRequestDTO,
    LogArtifactInfoResponseDTO,
    LogArtifactsInfoRequestDTO,
    LogArtifactsInfoResponseDTO,
    ArtifactsInfoResultDTO,
    ArtifactsInfoSummaryResultDTO,
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


@router.get("/summary/{project_id}", response_model=ArtifactsInfoSummaryResultDTO)
async def get_artifact_info_summary(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    artifact_type: list[str] | None = Query(default=None),
    artifact_name: list[str] | None = Query(default=None),
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
    max_steps: int = Query(default=1000, ge=1),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    service: ArtifactsInfoService = Depends(get_artifacts_info_service),
):
    return await service.get_artifacts_info_summary(
        project_id=project_id,
        experiment_id=experiment_id,
        artifact_types=artifact_type,
        artifact_names=artifact_name,
        limit=limit,
        offset=offset,
        max_steps=max_steps,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/detail/{project_id}", response_model=ArtifactsInfoResultDTO)
async def get_artifact_info_detail(
    project_id: UUID,
    experiment_id: UUID = Query(...),
    artifact_name: str = Query(..., min_length=1),
    step: int = Query(...),
    artifact_type: str | None = Query(default=None),
    service: ArtifactsInfoService = Depends(get_artifacts_info_service),
):
    try:
        return await service.get_artifacts_info_detail(
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_name=artifact_name,
            step=step,
            artifact_type=artifact_type,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
