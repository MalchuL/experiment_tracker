from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.experiments.dto import ExperimentCreateDTO, ExperimentUpdateDTO
from domain.experiments.mapper import ExperimentMapper
from models import Experiment, ExperimentStatus, Project, User


FEATURE_TREE = [
    {
        "name": "training",
        "children": [{"name": "optimizer-adam"}, {"name": "scheduler-cosine"}],
    }
]


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
    features: list[dict] | None = None,
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
        features=FEATURE_TREE if features is None else features,
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
            features=FEATURE_TREE,
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
        assert [feature.model_dump(exclude_none=True) for feature in dto.features] == FEATURE_TREE
        assert dto.progress == 5
        assert dto.color == "#123456"
        assert dto.order == 1
        assert dto.created_at == datetime(2024, 1, 1)
        assert dto.started_at == datetime(2024, 1, 2)
        assert dto.completed_at is None

    async def test_experiment_schema_to_dto_rejects_legacy_feature_object(
        self, db_session: AsyncSession, test_user: User
    ):
        mapper = ExperimentMapper()
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(
            db_session,
            project,
            features={},
        )

        with pytest.raises(ValidationError):
            mapper.experiment_schema_to_dto(experiment)

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
            features=[],
            progress=0,
        )

        dtos = mapper.experiment_list_schema_to_dto([experiment])

        assert len(dtos) == 1
        assert dtos[0].id == experiment.id
        assert dtos[0].name == "Experiment"
        assert dtos[0].status == ExperimentStatus.PLANNED
        assert dtos[0].features == []

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
            parent_experiment_id=parent.id,
            features=FEATURE_TREE,
            color="#123456",
            order=1,
        )
        experiment = mapper.experiment_create_dto_to_schema(dto)
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        assert experiment.project_id == dto.project_id
        assert experiment.parent_experiment_id == parent.id
        assert experiment.features == FEATURE_TREE
        assert experiment.color == "#123456"
        assert experiment.order == 1

    def test_experiment_update_dto_to_update_dict(self):
        mapper = ExperimentMapper()
        dto = ExperimentUpdateDTO(
            name="Updated",
            description="Updated description",
            status=ExperimentStatus.COMPLETE,
            features=[
                {
                    "name": "training",
                    "children": [{"name": "optimizer-sgd"}],
                }
            ],
            progress=10,
            order=2,
        )

        updates = mapper.experiment_update_dto_to_update_dict(dto)

        assert updates["name"] == "Updated"
        assert updates["description"] == "Updated description"
        assert updates["status"] == ExperimentStatus.COMPLETE
        assert updates["features"] == [
            {
                "name": "training",
                "children": [{"name": "optimizer-sgd"}],
            }
        ]
        assert updates["progress"] == 10
        assert updates["order"] == 2
