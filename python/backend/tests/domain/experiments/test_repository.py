from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.experiments.repository import ExperimentRepository
from lib.pagination import ListOptions
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
    description: str = "Repo experiment",
) -> Experiment:
    experiment = Experiment(
        project_id=project.id,
        name=name,
        description=description,
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
        names = {experiment.name for experiment in experiments.data}

        assert names == {"E1", "E2"}

    async def test_get_experiments_by_project_search_name(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        await _create_experiment(db_session, project, name="alpha-run")
        await _create_experiment(db_session, project, name="beta-run")

        page = await experiment_repository.get_experiments_by_project(
            project.id, list_options=ListOptions(limit=50, offset=0), search="Alpha"
        )
        assert {e.name for e in page.data} == {"alpha-run"}
        assert page.total == 1

    async def test_get_experiments_by_project_search_description(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        await _create_experiment(db_session, project, name="A", description="uses adam optimizer")
        await _create_experiment(db_session, project, name="B", description="sgd only")

        page = await experiment_repository.get_experiments_by_project(
            project.id, list_options=ListOptions(limit=50, offset=0), search="ADAM"
        )
        assert {e.name for e in page.data} == {"A"}

    async def test_get_experiments_by_project_search_id_fragment(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        e = await _create_experiment(db_session, project, name="solo")
        await _create_experiment(db_session, project, name="other")

        fragment = str(e.id).split("-")[0]
        page = await experiment_repository.get_experiments_by_project(
            project.id, list_options=ListOptions(limit=50, offset=0), search=fragment
        )
        assert len(page.data) == 1
        assert page.data[0].id == e.id
