from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from domain.hypotheses.dto import HypothesisCreateDTO, HypothesisUpdateDTO
from domain.hypotheses.mapper import HypothesisMapper
from models import Hypothesis, HypothesisStatus, Project, User


async def _create_project(
    db_session: AsyncSession, owner: User, name: str = "Mapper Project"
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Hypothesis mapper project",
        owner_id=owner.id,
        team_id=None,
        metrics=[],
        settings={},
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


async def _create_hypothesis(
    db_session: AsyncSession,
    project: Project,
    title: str = "Hypothesis",
    status: HypothesisStatus = HypothesisStatus.TESTING,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Hypothesis:
    hypothesis = Hypothesis(
        project_id=project.id,
        title=title,
        description="Desc",
        author="Author",
        status=status,
        target_metrics=["accuracy"],
        baseline="root",
        created_at=created_at,
        updated_at=updated_at,
    )
    db_session.add(hypothesis)
    await db_session.flush()
    await db_session.refresh(hypothesis)
    return hypothesis


class TestHypothesisMapper:
    async def test_hypothesis_schema_to_dto(
        self, db_session: AsyncSession, test_user: User
    ):
        mapper = HypothesisMapper()
        project = await _create_project(db_session, test_user)
        hypothesis = await _create_hypothesis(
            db_session,
            project,
            title="Hypothesis",
            status=HypothesisStatus.TESTING,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 2),
        )

        dto = mapper.hypothesis_schema_to_dto(hypothesis)

        assert dto.id == hypothesis.id
        assert dto.project_id == hypothesis.project_id
        assert dto.title == "Hypothesis"
        assert dto.description == "Desc"
        assert dto.author == "Author"
        assert dto.status == HypothesisStatus.TESTING
        assert dto.target_metrics == ["accuracy"]
        assert dto.baseline == "root"
        assert dto.created_at == datetime(2024, 1, 1)
        assert dto.updated_at == datetime(2024, 1, 2)

    async def test_hypothesis_list_schema_to_dto(
        self, db_session: AsyncSession, test_user: User
    ):
        mapper = HypothesisMapper()
        project = await _create_project(db_session, test_user)
        hypothesis = await _create_hypothesis(db_session, project, title="Hypothesis")

        dtos = mapper.hypothesis_list_schema_to_dto([hypothesis])

        assert len(dtos) == 1
        assert dtos[0].id == hypothesis.id
        assert dtos[0].title == "Hypothesis"
        assert dtos[0].status == HypothesisStatus.TESTING

    def test_hypothesis_create_dto_to_schema(self):
        mapper = HypothesisMapper()
        dto = HypothesisCreateDTO(
            project_id="223e4567-e89b-12d3-a456-426614174000",
            title="Create Hypothesis",
            description="Create description",
            author="Author",
            status=HypothesisStatus.PROPOSED,
            target_metrics=["accuracy"],
            baseline="root",
        )

        hypothesis = mapper.hypothesis_create_dto_to_schema(dto)

        assert str(hypothesis.project_id) == str(dto.project_id)
        assert hypothesis.title == "Create Hypothesis"
        assert hypothesis.description == "Create description"
        assert hypothesis.author == "Author"
        assert hypothesis.status == HypothesisStatus.PROPOSED
        assert hypothesis.target_metrics == ["accuracy"]
        assert hypothesis.baseline == "root"

    def test_hypothesis_update_dto_to_update_dict(self):
        mapper = HypothesisMapper()
        dto = HypothesisUpdateDTO(
            title="Updated",
            description="Updated description",
            author="Updated Author",
            status=HypothesisStatus.SUPPORTED,
            target_metrics=["latency"],
            baseline="new-baseline",
        )

        updates = mapper.hypothesis_update_dto_to_update_dict(dto)

        assert updates["title"] == "Updated"
        assert updates["description"] == "Updated description"
        assert updates["author"] == "Updated Author"
        assert updates["status"] == HypothesisStatus.SUPPORTED
        assert updates["target_metrics"] == ["latency"]
        assert updates["baseline"] == "new-baseline"
