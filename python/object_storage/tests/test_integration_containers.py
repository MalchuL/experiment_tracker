from __future__ import annotations

import hashlib
import io
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from object_storage.domain.project_artifacts_storage.dto import (
    SnapshotCreateRequestDTO,
    SnapshotFileEntryDTO,
)
from object_storage.domain.project_artifacts_storage.repository import (
    ObjectStorageRepository,
)
from object_storage.domain.project_artifacts_storage.service import ObjectStorageService
from object_storage.db.models import Base
from object_storage.storage.s3_client import get_s3_storage


@pytest.mark.asyncio
async def test_project_artifacts_workflow_with_isolated_containers(
    pytestconfig: pytest.Config,
) -> None:
    """
    Verify DB + object storage flow against isolated testcontainers.

    This test validates that runtime env overrides are enough to fully run
    upload/check/snapshot/delete logic without touching local dev services.
    """

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    payload = b"blob-payload-from-testcontainers"
    blob_hash = hashlib.sha256(payload).hexdigest()

    async with session_factory() as session:
        repository = ObjectStorageRepository(session)
        storage = get_s3_storage()
        service = ObjectStorageService(repository, storage)

        upload = UploadFile(filename="blob.bin", file=io.BytesIO(payload))
        upload_result = await service.upload_blob(project_id, blob_hash, upload)
        assert upload_result.status == "ok"

        check_result = await service.check_blobs(project_id, [blob_hash])
        assert check_result.missing == []

        snapshot_result = await service.create_snapshot(
            SnapshotCreateRequestDTO(
                project_id=project_id,
                experiment_id=uuid4(),
                files=[SnapshotFileEntryDTO(path="artifact.bin", hash=blob_hash)],
            )
        )
        snapshot_id = UUID(snapshot_result.snapshot_id)

        with pytest.raises(HTTPException, match="referenced by a snapshot") as exc_info:
            await service.delete_blob(project_id, blob_hash)
        assert exc_info.value.status_code == 400

        deleted_blobs = await service.delete_snapshot(project_id, snapshot_id)
        assert deleted_blobs == [blob_hash]

        delete_result = await service.delete_blob(project_id, blob_hash)
        assert delete_result.deleted is False

    await engine.dispose()
