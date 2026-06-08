"""Application-service tests for importance job creation and retrieval."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mltools.config.settings import Settings
from mltools.domain.hparam_importance.dto import CreateJobDTO, TargetMetricDTO
from mltools.db.models import Base
from mltools.domain.hparam_importance.service import JobService


class Dispatcher:
    """Record the identifier submitted by the job service."""

    def __init__(self):
        """Initialize the dispatcher without a submitted job.

        Args:
            None.

        Returns:
            None.
        """
        self.job_id = None

    def dispatch(self, job_id):
        """Record a dispatched job identifier.

        Args:
            job_id: Identifier submitted for asynchronous processing.

        Returns:
            None.
        """
        self.job_id = job_id


@pytest.mark.asyncio
async def test_create_list_and_get_job() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    project_id = uuid4()
    user_id = uuid4()
    dispatcher = Dispatcher()
    async with maker() as session:
        service = JobService(
            session,
            dispatcher,
            Settings(min_experiments_per_metric=2).hparam_importance_settings(),
        )
        created = await service.create(
            project_id,
            CreateJobDTO(
                target_metrics=[TargetMetricDTO(name="loss")],
                requested_by_user_id=user_id,
            ),
        )
        listed = await service.list(project_id, 20, 0)
        fetched = await service.get(project_id, created.job_id)

    assert dispatcher.job_id == created.job_id
    assert listed.total == 1
    assert fetched.target_metrics[0].name == "loss"
    await engine.dispose()
