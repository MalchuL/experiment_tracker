from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from db.database import get_async_session
from models import User
from domain.rbac.permissions import ProjectActions

from .dto import MetricDTO, MetricCreateDTO
from .error import MetricNotAccessibleError, MetricNotFoundError
from .service import MetricService

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _raise_metric_http_error(error: Exception) -> None:
    if isinstance(error, MetricNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, MetricNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.post("", response_model=MetricDTO)
async def create_metric(
    data: MetricCreateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_METRIC)),
    session: AsyncSession = Depends(get_async_session),
):
    service = MetricService(session)
    try:
        return await service.create_metric(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_metric_http_error(exc)


# TODO: implement service methods for additional metric routes if added.
