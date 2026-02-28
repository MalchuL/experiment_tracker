from uuid import UUID

from fastapi import APIRouter, Depends

from api.service_dependencies import get_last_logged_service
from .dto import LastLoggedExperimentsRequestDTO, LastLoggedExperimentsResultDTO
from .service import LastLoggedService

router = APIRouter(prefix="/last_logged", tags=["last_logged"])


@router.post(
    "/{project_id}",
    response_model=LastLoggedExperimentsResultDTO,
)
async def get_last_logged_experiments(
    project_id: UUID,
    payload: LastLoggedExperimentsRequestDTO,
    service: LastLoggedService = Depends(get_last_logged_service),
):
    return await service.get_last_logged_experiments(
        project_id,
        experiment_ids=payload.experiment_ids,
    )
