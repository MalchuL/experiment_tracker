"""FastAPI dependency providers for domain services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from api.cache import get_cache
from app.infrastructure.cache.cache import Cache
from db.clickhouse import get_clickhouse_client

if TYPE_CHECKING:
    from app.domain.last_logged.service import LastLoggedService
    from app.domain.artifacts_info.service import ArtifactsInfoService
    from app.domain.projects.service import ProjectsService
    from app.domain.scalars.service import ScalarsService


async def get_last_logged_service(
    client=Depends(get_clickhouse_client),
) -> "LastLoggedService":
    from app.domain.last_logged.service import LastLoggedService

    return LastLoggedService(client)


async def get_scalars_service(
    client=Depends(get_clickhouse_client),
    cache: Cache | None = Depends(get_cache),
    last_logged_service: "LastLoggedService" = Depends(get_last_logged_service),
) -> "ScalarsService":
    from app.domain.scalars.service import ScalarsService

    return ScalarsService(client, cache, last_logged_service)


async def get_artifacts_info_service(
    client=Depends(get_clickhouse_client),
    last_logged_service: "LastLoggedService" = Depends(get_last_logged_service),
) -> "ArtifactsInfoService":
    from app.domain.artifacts_info.service import ArtifactsInfoService

    return ArtifactsInfoService(client, last_logged_service)


async def get_projects_service(
    scalars_service: "ScalarsService" = Depends(get_scalars_service),
    artifacts_info_service: "ArtifactsInfoService" = Depends(get_artifacts_info_service),
    last_logged_service: "LastLoggedService" = Depends(get_last_logged_service),
) -> "ProjectsService":
    from app.domain.projects.service import ProjectsService

    return ProjectsService(scalars_service, artifacts_info_service, last_logged_service)
