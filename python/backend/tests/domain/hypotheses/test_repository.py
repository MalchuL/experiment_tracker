from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.hypotheses.repository import HypothesisRepository
from models import Hypothesis, HypothesisStatus, Project, User


async def _create_project(
    db_session: AsyncSession, owner: User, name: str = "Repo Project"
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Hypothesis repo project",
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
    title: str,
    created_at: datetime | None = None,
    status: HypothesisStatus = HypothesisStatus.PROPOSED,
) -> Hypothesis:
    hypothesis = Hypothesis(
        project_id=project.id,
        title=title,
        description="Repo hypothesis",
        author="Repo Author",
        status=status,
        target_metrics=["accuracy"],
        baseline="root",
        created_at=created_at,
    )
    db_session.add(hypothesis)
    await db_session.flush()
    await db_session.refresh(hypothesis)
    return hypothesis


class TestHypothesisRepository:
    @pytest.fixture
    def hypothesis_repository(self, db_session: AsyncSession) -> HypothesisRepository:
        return HypothesisRepository(db_session)

    async def test_get_hypotheses_by_project_filters(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        other_project = await _create_project(db_session, test_user, name="Other")
        await _create_hypothesis(db_session, project, title="H1")
        await _create_hypothesis(db_session, project, title="H2")
        await _create_hypothesis(db_session, other_project, title="Other")

        hypotheses = await hypothesis_repository.get_hypotheses_by_project(project.id)
        titles = {hypothesis.title for hypothesis in hypotheses}

        assert titles == {"H1", "H2"}

    async def test_get_hypotheses_by_project_orders_desc(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project_a = await _create_project(db_session, test_user, name="A")
        project_b = await _create_project(db_session, test_user, name="B")
        await _create_hypothesis(
            db_session,
            project_a,
            title="Older",
            created_at=datetime(2024, 1, 1),
        )
        await _create_hypothesis(
            db_session,
            project_b,
            title="Newer",
            created_at=datetime(2024, 1, 2),
        )

        hypotheses = await hypothesis_repository.get_hypotheses_by_project(
            [project_a.id, project_b.id]
        )
        titles = [hypothesis.title for hypothesis in hypotheses]

        assert titles == ["Newer", "Older"]
