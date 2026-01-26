from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import current_active_user
from db.database import get_async_session
from models import User

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
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = MetricService(session)
    try:
        return await service.create_metric(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_metric_http_error(exc)


# TODO: implement service methods for additional metric routes if added.
