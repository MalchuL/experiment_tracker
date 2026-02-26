from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from object_storage.db import get_async_session
from object_storage.storage import StorageBackend, get_storage
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from object_storage.domain.experiment_artifacts_storage.service import (
        ArtifactsStorageService,
    )
    from object_storage.domain.project_artifacts_storage.repository import (
        ObjectStorageRepository,
    )
    from object_storage.domain.project_artifacts_storage.service import (
        ObjectStorageService,
    )


async def get_project_artifacts_repository(
    session: AsyncSession = Depends(get_async_session),
) -> "ObjectStorageRepository":
    from object_storage.domain.project_artifacts_storage.repository import (
        ObjectStorageRepository,
    )

    return ObjectStorageRepository(session)


async def get_project_artifacts_service(
    repository: "ObjectStorageRepository" = Depends(get_project_artifacts_repository),
    storage: StorageBackend = Depends(get_storage),
) -> "ObjectStorageService":
    from object_storage.domain.project_artifacts_storage.service import (
        ObjectStorageService,
    )

    return ObjectStorageService(repository, storage)


async def get_experiment_artifacts_service(
    storage: StorageBackend = Depends(get_storage),
) -> "ArtifactsStorageService":
    from object_storage.domain.experiment_artifacts_storage.service import (
        ArtifactsStorageService,
    )

    return ArtifactsStorageService(storage)
