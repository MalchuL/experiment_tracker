"""FastAPI dependency providers for domain services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from api.cache import get_cache
from app.infrastructure.cache.cache import Cache
from db.clickhouse import get_clickhouse_client

if TYPE_CHECKING:
    from app.domain.objects.service import ObjectsService
    from app.domain.projects.service import ProjectsService
    from app.domain.scalars.service import ScalarsService


async def get_scalars_service(
    client=Depends(get_clickhouse_client),
    cache: Cache | None = Depends(get_cache),
) -> "ScalarsService":
    from app.domain.scalars.service import ScalarsService

    return ScalarsService(client, cache)


async def get_objects_service(
    client=Depends(get_clickhouse_client),
) -> "ObjectsService":
    from app.domain.objects.service import ObjectsService

    return ObjectsService(client)


async def get_projects_service(
    client=Depends(get_clickhouse_client),
) -> "ProjectsService":
    from app.domain.projects.service import ProjectsService

    return ProjectsService(client)
