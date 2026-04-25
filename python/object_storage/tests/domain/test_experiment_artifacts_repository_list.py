"""Integration tests for ``ExperimentArtifactsRepository.list_experiment_blobs``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from object_storage.db.models import Base, ExperimentBlob
from object_storage.domain.experiment_artifacts_storage.repository import (
    ExperimentArtifactsRepository,
)


def _maxish_file_path(index: int) -> str:
    """Build a path near ``ExperimentBlob.file_path``'s 1024-char limit (unique per index)."""

    prefix = f"experiments/run_{index:05d}/checkpoints/"
    suffix = ".pt"
    pad_len = 1024 - len(prefix) - len(suffix)
    assert pad_len > 0
    return f"{prefix}{'p' * pad_len}{suffix}"


@pytest.mark.asyncio
async def test_list_experiment_blobs_long_file_paths_list_filter(
    pytestconfig: pytest.Config,
) -> None:
    """Many long paths in ``file_paths`` must filter correctly (``IN`` + totals + pagination)."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    n_rows = 72
    base_time = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    stored_paths: list[str] = []

    async with session_factory() as session:
        for i in range(n_rows):
            path = _maxish_file_path(i)
            assert len(path) == 1024
            stored_paths.append(path)
            session.add(
                ExperimentBlob(
                    project_id=project_id,
                    experiment_id=experiment_id,
                    artifact_hash=f"{i:064d}",
                    file_path=path,
                    mime_type="application/octet-stream",
                    size=256 + i,
                    created_at=base_time + timedelta(milliseconds=i),
                    updated_at=base_time + timedelta(milliseconds=i),
                )
            )
        await session.commit()

    bogus_paths = [_maxish_file_path(10_000 + j) for j in range(40)]
    filter_paths = stored_paths + bogus_paths

    async with session_factory() as session:
        repo = ExperimentArtifactsRepository(session)
        blobs, total = await repo.list_experiment_blobs(
            project_id,
            experiment_id,
            limit=500,
            offset=0,
            file_paths=filter_paths,
        )
        assert total == n_rows
        assert len(blobs) == n_rows
        returned_paths = {b.file_path for b in blobs}
        assert returned_paths == set(stored_paths)

        page, page_total = await repo.list_experiment_blobs(
            project_id,
            experiment_id,
            limit=15,
            offset=30,
            file_paths=stored_paths,
        )
        assert page_total == n_rows
        assert len(page) == 15

    await engine.dispose()


@pytest.mark.asyncio
async def test_list_experiment_blobs_total_stable_across_limit_offset(
    pytestconfig: pytest.Config,
) -> None:
    """``total`` must match the full filtered row count for every page (window + COUNT fallback)."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    n_rows = 5
    # Columns are TIMESTAMP WITHOUT TIME ZONE; use naive UTC wall time.
    base_time = datetime.now(UTC).replace(tzinfo=None, microsecond=0)

    async with session_factory() as session:
        for i in range(n_rows):
            session.add(
                ExperimentBlob(
                    project_id=project_id,
                    experiment_id=experiment_id,
                    artifact_hash=f"{i:064d}",
                    file_path=f"artifacts/blob_{i}.bin",
                    mime_type="application/octet-stream",
                    size=100 + i,
                    created_at=base_time + timedelta(seconds=i),
                    updated_at=base_time + timedelta(seconds=i),
                )
            )
        await session.commit()

    async with session_factory() as session:
        repo = ExperimentArtifactsRepository(session)
        pages: list[tuple[int, int, int]] = []
        for offset in (0, 2, 4, 6):
            blobs, total = await repo.list_experiment_blobs(
                project_id,
                experiment_id,
                limit=2,
                offset=offset,
            )
            pages.append((offset, len(blobs), total))

    assert pages == [
        (0, 2, n_rows),
        (2, 2, n_rows),
        (4, 1, n_rows),
        (6, 0, n_rows),
    ]
    totals = {t for _, _, t in pages}
    assert totals == {n_rows}, "total must be identical for every limit/offset window"

    await engine.dispose()
