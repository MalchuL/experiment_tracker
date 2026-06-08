"""Tests for MLTools worker job-state transitions and failure messages."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mltools.db.models import Base, HparamImportanceJob, HparamImportanceJobMessage
from mltools.workers import hparam_importance as tasks


async def make_job(maker) -> HparamImportanceJob:
    """Persist a pending job for worker tests.

    Args:
        maker: Async SQLAlchemy session factory used to persist the job.

    Returns:
        Refreshed pending job instance with its generated identifier.
    """
    async with maker() as session:
        job = HparamImportanceJob(
            project_id=uuid4(),
            status="pending",
            stage="created",
            progress=0,
            target_metrics=[{"name": "loss", "label": None}],
            config={},
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


@pytest.mark.asyncio
async def test_process_marks_completed(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    job = await make_job(maker)

    async def successful(session, job, **kwargs):
        return 1

    monkeypatch.setattr(tasks, "session_maker", maker)
    monkeypatch.setattr(tasks, "run_analysis", successful)
    await tasks._process(job.id)

    async with maker() as session:
        updated = await session.get(HparamImportanceJob, job.id)
        assert updated.status == "completed"
        assert updated.progress == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_process_marks_failed_and_stores_message(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    job = await make_job(maker)

    async def failed(session, job, **kwargs):
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(tasks, "session_maker", maker)
    monkeypatch.setattr(tasks, "run_analysis", failed)
    await tasks._process(job.id)

    async with maker() as session:
        updated = await session.get(HparamImportanceJob, job.id)
        message = await session.scalar(
            select(HparamImportanceJobMessage).where(
                HparamImportanceJobMessage.job_id == job.id
            )
        )
        assert updated.status == "failed"
        assert updated.error_message == "backend unavailable"
        assert message.category == "training_failed"
    await engine.dispose()
