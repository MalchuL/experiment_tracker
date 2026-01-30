from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from db.database import get_async_session
from models import User
from domain.rbac.permissions import ProjectActions

from .dto import HypothesisCreateDTO, HypothesisDTO, HypothesisUpdateDTO
from .error import HypothesisNotAccessibleError, HypothesisNotFoundError
from .service import HypothesisService

router = APIRouter(prefix="/hypotheses", tags=["hypotheses"])


def _raise_hypothesis_http_error(error: Exception) -> None:
    if isinstance(error, HypothesisNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, HypothesisNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.get("", response_model=List[HypothesisDTO])
async def get_all_hypotheses(
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_HYPOTHESIS)),
    session: AsyncSession = Depends(get_async_session),
):
    service = HypothesisService(session)
    try:
        return await service.get_accessible_hypotheses(user)
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)


@router.get("/recent", response_model=List[HypothesisDTO])
async def get_recent_hypotheses(
    projectId: UUID,
    limit: int = 10,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_HYPOTHESIS)),
    session: AsyncSession = Depends(get_async_session),
):
    print(projectId)
    print(user)
    service = HypothesisService(session)
    return await service.get_hypotheses_by_project(user, projectId, limit=limit)


@router.get("/{hypothesis_id}", response_model=HypothesisDTO)
async def get_hypothesis(
    hypothesis_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_HYPOTHESIS)),
    session: AsyncSession = Depends(get_async_session),
):
    service = HypothesisService(session)
    try:
        return await service.get_hypothesis_if_accessible(user, hypothesis_id)
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)


@router.post("", response_model=HypothesisDTO)
async def create_hypothesis(
    data: HypothesisCreateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_HYPOTHESIS)),
    session: AsyncSession = Depends(get_async_session),
):
    service = HypothesisService(session)
    try:
        return await service.create_hypothesis(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)


@router.patch("/{hypothesis_id}", response_model=HypothesisDTO)
async def update_hypothesis(
    hypothesis_id: UUID,
    data: HypothesisUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_HYPOTHESIS)),
    session: AsyncSession = Depends(get_async_session),
):
    service = HypothesisService(session)
    try:
        return await service.update_hypothesis(user, hypothesis_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)


@router.delete("/{hypothesis_id}")
async def delete_hypothesis(
    hypothesis_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_HYPOTHESIS)),
    session: AsyncSession = Depends(get_async_session),
):
    service = HypothesisService(session)
    try:
        success = await service.delete_hypothesis(user, hypothesis_id)
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return {"success": True}
