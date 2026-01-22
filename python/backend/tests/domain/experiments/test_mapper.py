from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.experiments.dto import ExperimentCreateDTO, ExperimentUpdateDTO
from domain.experiments.mapper import CreateDTOToSchemaProps, ExperimentMapper
from domain.experiments.utils import ExperimentParseResult
from models import Experiment, ExperimentStatus, Project, User


async def _create_project(
    db_session: AsyncSession, owner: User, name: str = "Mapper Project"
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Experiment mapper project",
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
    name: str = "Experiment",
    status: ExperimentStatus = ExperimentStatus.RUNNING,
    created_at: datetime | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    features: dict | None = None,
    features_diff: dict | None = None,
    git_diff: str | None = None,
    progress: int | None = None,
    color: str | None = None,
    order: int | None = None,
) -> Experiment:
    experiment = Experiment(
        project_id=project.id,
        name=name,
        description="Desc",
        status=status,
        parent_experiment_id=None,
        features={"lr": 0.1} if features is None else features,
        features_diff=features_diff,
        git_diff=git_diff,
        progress=progress,
        color=color,
        order=order,
        created_at=created_at,
        started_at=started_at,
        completed_at=completed_at,
    )
    db_session.add(experiment)
    await db_session.flush()
    await db_session.refresh(experiment)
    return experiment


class TestExperimentMapper:
    def test_experiment_parse_result_to_dto(self):
        mapper = ExperimentMapper()
        result = ExperimentParseResult(num="1", parent="root", change="seed")

        dto = mapper.experiment_parse_result_to_dto(result)

        assert dto.num == "1"
        assert dto.parent == "root"
        assert dto.change == "seed"

    async def test_experiment_schema_to_dto(
        self, db_session: AsyncSession, test_user: User
    ):
        mapper = ExperimentMapper()
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(
            db_session,
            project,
            name="Experiment",
            status=ExperimentStatus.RUNNING,
            created_at=datetime(2024, 1, 1),
            started_at=datetime(2024, 1, 2),
            completed_at=None,
            features={"lr": 0.1},
            features_diff={"lr": 0.05},
            git_diff="diff",
            progress=5,
            color="#123456",
            order=1,
        )

        dto = mapper.experiment_schema_to_dto(experiment)

        assert dto.id == experiment.id
        assert dto.project_id == experiment.project_id
        assert dto.name == "Experiment"
        assert dto.description == "Desc"
        assert dto.status == ExperimentStatus.RUNNING
        assert dto.parent_experiment_id is None
        assert dto.features == {"lr": 0.1}
        assert dto.features_diff == {"lr": 0.05}
        assert dto.git_diff == "diff"
        assert dto.progress == 5
        assert dto.color == "#123456"
        assert dto.order == 1
        assert dto.created_at == datetime(2024, 1, 1)
        assert dto.started_at == datetime(2024, 1, 2)
        assert dto.completed_at is None

    async def test_experiment_list_schema_to_dto(
        self, db_session: AsyncSession, test_user: User
    ):
        mapper = ExperimentMapper()
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(
            db_session,
            project,
            name="Experiment",
            status=ExperimentStatus.PLANNED,
            created_at=datetime(2024, 1, 1),
            features={},
            progress=0,
        )

        dtos = mapper.experiment_list_schema_to_dto([experiment])

        assert len(dtos) == 1
        assert dtos[0].id == experiment.id
        assert dtos[0].name == "Experiment"
        assert dtos[0].status == ExperimentStatus.PLANNED
        assert dtos[0].features == {}

    async def test_experiment_create_dto_to_schema_uses_parent_props(
        self, db_session: AsyncSession, test_user: User
    ):
        mapper = ExperimentMapper()
        project = await _create_project(db_session, test_user)
        parent = await _create_experiment(
            db_session,
            project,
            name="Parent",
            status=ExperimentStatus.PLANNED,
        )
        dto = ExperimentCreateDTO(
            project_id=project.id,
            name="Experiment",
            description="Desc",
            status=ExperimentStatus.PLANNED,
            parent_experiment_id=None,
            features={"lr": 0.1},
            git_diff="diff",
            color="#123456",
            order=1,
        )
        props = CreateDTOToSchemaProps(
            owner_id=test_user.id,
            parent_experiment_id=parent.id,
        )

        experiment = mapper.experiment_create_dto_to_schema(dto, props)
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        assert experiment.project_id == dto.project_id
        assert experiment.parent_experiment_id == parent.id
        assert experiment.features == {"lr": 0.1}
        assert experiment.git_diff == "diff"
        assert experiment.color == "#123456"
        assert experiment.order == 1

    def test_experiment_update_dto_to_update_dict(self):
        mapper = ExperimentMapper()
        dto = ExperimentUpdateDTO(
            name="Updated",
            description="Updated description",
            status=ExperimentStatus.COMPLETE,
            features={"lr": 0.2},
            git_diff="diff",
            progress=10,
            order=2,
        )

        updates = mapper.experiment_update_dto_to_update_dict(dto)

        assert updates["name"] == "Updated"
        assert updates["description"] == "Updated description"
        assert updates["status"] == ExperimentStatus.COMPLETE
        assert updates["features"] == {"lr": 0.2}
        assert updates["git_diff"] == "diff"
        assert updates["progress"] == 10
        assert updates["order"] == 2
