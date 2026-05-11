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
    session: AsyncSession = Depends(get_async_session),
    storage: StorageBackend = Depends(get_storage),
) -> "ObjectStorageService":
    from object_storage.domain.buckets.repository import BucketsRepository
    from object_storage.domain.buckets.service import BucketRegistryService
    from object_storage.domain.experiment_artifacts_storage.repository import (
        ExperimentArtifactsRepository,
    )
    from object_storage.domain.project_artifacts_storage.repository import (
        ObjectStorageRepository,
    )
    from object_storage.domain.project_artifacts_storage.service import (
        ObjectStorageService,
    )

    buckets_service = BucketRegistryService(BucketsRepository(session), storage)
    repository = ObjectStorageRepository(session)
    experiment_repository = ExperimentArtifactsRepository(session)
    return ObjectStorageService(repository, buckets_service, experiment_repository)


async def get_experiment_artifacts_service(
    session: AsyncSession = Depends(get_async_session),
    storage: StorageBackend = Depends(get_storage),
) -> "ArtifactsStorageService":
    from object_storage.domain.buckets.repository import BucketsRepository
    from object_storage.domain.buckets.service import BucketRegistryService
    from object_storage.domain.experiment_artifacts_storage.repository import (
        ExperimentArtifactsRepository,
    )
    from object_storage.domain.experiment_artifacts_storage.service import (
        ArtifactsStorageService,
    )

    buckets_service = BucketRegistryService(BucketsRepository(session), storage)
    artifacts_repository = ExperimentArtifactsRepository(session)
    return ArtifactsStorageService(buckets_service, artifacts_repository)
