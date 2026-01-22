from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.experiments.repository import ExperimentRepository
from models import Experiment, ExperimentStatus, Project, User


async def _create_project(
    db_session: AsyncSession, owner: User, name: str = "Repo Project"
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Experiment repo project",
        owner_id=owner.id,
        team_id=None,
        metrics=[],
        settings={},
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


async def _create_experiment(
    db_session: AsyncSession,
    project: Project,
    name: str,
    started_by: User | None = None,
    created_at: datetime | None = None,
    status: ExperimentStatus = ExperimentStatus.PLANNED,
) -> Experiment:
    experiment = Experiment(
        project_id=project.id,
        name=name,
        description="Repo experiment",
        status=status,
        started_by=started_by.id if started_by else None,
        created_at=created_at,
    )
    db_session.add(experiment)
    await db_session.flush()
    await db_session.refresh(experiment)
    return experiment


class TestExperimentRepository:
    @pytest.fixture
    def experiment_repository(self, db_session: AsyncSession) -> ExperimentRepository:
        return ExperimentRepository(db_session)

    async def test_get_user_experiments_filters_by_started_by(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        await _create_experiment(
            db_session,
            project,
            name="Owned A",
            started_by=test_user,
            created_at=datetime(2024, 1, 1),
        )
        experiment_b = await _create_experiment(
            db_session,
            project,
            name="Owned B",
            started_by=test_user,
            created_at=datetime(2024, 1, 2),
        )
        print(experiment_b.id, experiment_b.started_by)
        await _create_experiment(
            db_session,
            project,
            name="Other user",
            started_by=test_user_2,
            created_at=datetime(2024, 1, 3),
        )

        experiments = await experiment_repository.get_user_experiments(test_user)
        names = [experiment.name for experiment in experiments]

        assert names == ["Owned B", "Owned A"]

    async def test_get_experiments_by_project(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        await _create_experiment(db_session, project, name="E1")
        await _create_experiment(db_session, project, name="E2")

        experiments = await experiment_repository.get_experiments_by_project(project.id)
        names = {experiment.name for experiment in experiments}

        assert names == {"E1", "E2"}
