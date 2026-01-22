import pytest

from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.repository import ProjectRepository
from models import Project, Team, User


async def _create_team(
    db_session: AsyncSession, owner: User, name: str = "Project Repo Team"
) -> Team:
    team = Team(
        id=None,
        name=name,
        description="Team for project repository tests",
        owner_id=owner.id,
    )
    db_session.add(team)
    await db_session.flush()
    await db_session.refresh(team)
    return team


async def _create_project(
    db_session: AsyncSession,
    owner: User,
    team: Team | None = None,
    name: str = "Project Repo",
) -> Project:
    team_id = team.id if team is not None else None
    project = Project(
        id=None,
        name=name,
        description="Project repository test",
        owner_id=owner.id,
        team_id=team_id,
        metrics=[],
        settings={},
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


class TestProjectRepository:
    @pytest.fixture
    def project_repository(self, db_session: AsyncSession) -> ProjectRepository:
        return ProjectRepository(db_session)

    async def test_get_project_by_id_full_load(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        project = await _create_project(db_session, test_user, team=team)
        db_session.expunge_all()

        loaded = await project_repository.get_project_by_id(project.id, full_load=True)

        assert loaded is not None
        assert loaded.id == project.id
        assert loaded.owner.id == test_user.id
        assert loaded.team is not None
        assert loaded.team.id == team.id
        assert loaded.experiments == []
        assert loaded.hypotheses == []

    async def test_get_project_by_id_no_load_raises_on_relationship_access(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        project = await _create_project(db_session, test_user, team=team)
        db_session.expunge_all()

        loaded = await project_repository.get_project_by_id(project.id, full_load=False)

        assert loaded is not None
        with pytest.raises(InvalidRequestError):
            _ = loaded.owner

    async def test_get_projects_by_ids_returns_empty_for_empty_list(
        self, project_repository: ProjectRepository
    ) -> None:
        assert await project_repository.get_projects_by_ids([]) == []

    async def test_get_projects_by_ids_returns_requested_projects(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project_1 = await _create_project(db_session, test_user, name="Repo One")
        project_2 = await _create_project(db_session, test_user, name="Repo Two")
        db_session.expunge_all()

        projects = await project_repository.get_projects_by_ids(
            [project_1.id, project_2.id], full_load=True
        )
        project_ids = {project.id for project in projects}
        assert project_ids == {project_1.id, project_2.id}

    async def test_get_projects_by_team_filters_projects(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user, name="Allowed Team")
        other_team = await _create_team(db_session, test_user, name="Hidden Team")
        allowed = await _create_project(
            db_session, test_user, team=team, name="Allowed"
        )
        await _create_project(db_session, test_user, team=other_team, name="Hidden")
        db_session.expunge_all()

        projects = await project_repository.get_projects_by_team(team.id)
        project_ids = {project.id for project in projects}
        assert project_ids == {allowed.id}
