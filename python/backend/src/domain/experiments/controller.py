from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import current_active_user
from db.database import get_async_session
from models import User

from .dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentReorderDTO,
    ExperimentUpdateDTO,
)
from .error import ExperimentNamePatternNotSetError, ExperimentNotAccessibleError
from .service import ExperimentService

router = APIRouter(prefix="/experiments", tags=["experiments"])


def _raise_experiment_http_error(error: Exception) -> None:
    if isinstance(error, ExperimentNotAccessibleError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ExperimentNamePatternNotSetError):
        raise HTTPException(status_code=400, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.get("/recent", response_model=List[ExperimentDTO])
async def get_recent_experiments(
    limit: int = 10,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ExperimentService(session)
    try:
        return await service.get_recent_experiments(user, limit)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.get("/{experiment_id}", response_model=ExperimentDTO)
async def get_experiment(
    experiment_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ExperimentService(session)
    try:
        return await service.get_experiment_if_accessible(user, experiment_id)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.post("", response_model=ExperimentDTO)
async def create_experiment(
    data: ExperimentCreateDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ExperimentService(session)
    try:
        return await service.create_experiment(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.patch("/{experiment_id}", response_model=ExperimentDTO)
async def update_experiment(
    experiment_id: UUID,
    data: ExperimentUpdateDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ExperimentService(session)
    try:
        return await service.update_experiment(user, experiment_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.delete("/{experiment_id}")
async def delete_experiment(
    experiment_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ExperimentService(session)
    try:
        success = await service.delete_experiment(user, experiment_id)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"success": True}


@router.post("/reorder")
async def reorder_experiments(
    data: ExperimentReorderDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ExperimentService(session)
    try:
        await service.reorder_experiments(user, data.project_id, data.experiment_ids)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)
    return {"success": True}


# TODO: implement service methods for these routes
# - GET /experiments/{experiment_id}/metrics
