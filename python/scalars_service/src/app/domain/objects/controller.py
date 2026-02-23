from datetime import datetime
from uuid import UUID

from api.cache import get_cache
from app.infrastructure.cache.cache import Cache
from db.clickhouse import get_clickhouse_client
from fastapi import APIRouter, Depends, HTTPException, Query

from .dto import (
    LogObjectRequestDTO,
    LogObjectResponseDTO,
    LogObjectsRequestDTO,
    LogObjectsResponseDTO,
    ObjectsResultDTO,
)
from .service import ObjectsService

router = APIRouter(prefix="/objects", tags=["objects"])


@router.post("/log/{project_id}/{experiment_id}", response_model=LogObjectResponseDTO)
async def log_object(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogObjectRequestDTO,
    client=Depends(get_clickhouse_client),
    _cache: Cache | None = Depends(get_cache),
):
    try:
        service = ObjectsService(client)
        return await service.log_object(project_id, experiment_id, payload)
    except ValueError as exc:
        if str(exc) == "Objects table does not exist":
            raise HTTPException(status_code=404, detail=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/log_batch/{project_id}/{experiment_id}",
    response_model=LogObjectsResponseDTO,
)
async def log_objects_batch(
    project_id: UUID,
    experiment_id: UUID,
    payload: LogObjectsRequestDTO,
    client=Depends(get_clickhouse_client),
    _cache: Cache | None = Depends(get_cache),
):
    service = ObjectsService(client)
    return await service.log_objects(project_id, experiment_id, payload)


@router.get("/get/{project_id}", response_model=ObjectsResultDTO)
async def get_objects(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    object_type: list[str] | None = Query(default=None),
    name: list[str] | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    client=Depends(get_clickhouse_client),
    _cache: Cache | None = Depends(get_cache),
):
    service = ObjectsService(client)
    return await service.get_objects(
        project_id=project_id,
        experiment_id=experiment_id,
        object_types=object_type,
        names=name,
        start_time=start_time,
        end_time=end_time,
    )
