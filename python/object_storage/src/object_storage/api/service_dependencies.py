from object_storage.domain.object_storage.repository import ObjectStorageRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from object_storage.db import get_async_session
from object_storage.storage import StorageBackend, get_storage
from object_storage.domain.object_storage.service import ObjectStorageService


async def get_object_storage_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ObjectStorageRepository:
    return ObjectStorageRepository(session)


async def get_object_storage_service(
    repository: ObjectStorageRepository = Depends(get_object_storage_repository),
    storage: StorageBackend = Depends(get_storage),
) -> ObjectStorageService:
    return ObjectStorageService(repository, storage)
