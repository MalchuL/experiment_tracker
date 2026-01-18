import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.permissions.project import role_to_project_permissions
from domain.rbac.permissions.team import TeamActions, role_to_team_permissions
from domain.rbac.repository import PermissionRepository
from domain.rbac.strategies.project import ProjectRbacStrategy
from domain.rbac.strategies.team import TeamRbacStrategy
from models import Permission, Project, Team, TeamRole, User


async def _create_team(db_session: AsyncSession, owner: User) -> Team:
    team = Team(
        id=None,
        name="RBAC Team",
        description="Team for RBAC strategy tests",
        owner_id=owner.id,
    )
    db_session.add(team)
    await db_session.flush()
    await db_session.refresh(team)
    return team


async def _create_project(
    db_session: AsyncSession, owner: User, team: Team | None = None, name: str = "P1"
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="RBAC project",
        owner_id=owner.id,
        team_id=team.id if team else None,
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


class TestProjectRbacStrategy:
    @pytest.fixture
    def project_strategy(self, db_session: AsyncSession) -> ProjectRbacStrategy:
        return ProjectRbacStrategy(db_session, auto_commit=True)

    async def test_add_update_remove_project_member(
        self,
        project_strategy: ProjectRbacStrategy,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        await project_strategy.add_project_member_permissions(
            project.id, test_user.id, TeamRole.MEMBER
        )

        repo = PermissionRepository(db_session)
        permissions = await repo.get_permissions(
            user_id=test_user.id, project_id=project.id
        )
        assert len(permissions) == len(role_to_project_permissions(TeamRole.MEMBER))

        await project_strategy.update_project_member_role_permissions(
            project.id, test_user.id, TeamRole.VIEWER
        )
        updated = await repo.get_permissions(
            user_id=test_user.id, project_id=project.id
        )
        expected = role_to_project_permissions(TeamRole.VIEWER)
        assert all(
            permission.allowed == expected[permission.action] for permission in updated
        )

        await project_strategy.remove_project_member_permissions(
            project.id, test_user.id
        )
        remaining = await repo.get_permissions(
            user_id=test_user.id, project_id=project.id
        )
        assert remaining == []

    async def test_get_user_accessible_projects_with_action_filter(
        self,
        project_strategy: ProjectRbacStrategy,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project1 = await _create_project(db_session, test_user, name="Project A")
        project2 = await _create_project(db_session, test_user, name="Project B")

        repo = PermissionRepository(db_session)
        await repo.create_permission(
            Permission(
                user_id=test_user.id,
                action="project.view",
                allowed=True,
                project_id=project1.id,
            )
        )
        await repo.create_permission(
            Permission(
                user_id=test_user.id,
                action="project.edit",
                allowed=True,
                project_id=project2.id,
            )
        )

        results = await project_strategy.get_user_accessible_projects(
            test_user.id, actions="project.view"
        )
        assert {project.id for project in results} == {project1.id}


class TestTeamRbacStrategy:
    @pytest.fixture
    def team_strategy(self, db_session: AsyncSession) -> TeamRbacStrategy:
        return TeamRbacStrategy(db_session, auto_commit=True)

    async def test_add_update_remove_team_member(
        self,
        team_strategy: TeamRbacStrategy,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        project1 = await _create_project(db_session, test_user, team=team, name="T1")
        project2 = await _create_project(db_session, test_user, team=team, name="T2")
        standalone = await _create_project(
            db_session, test_user, team=None, name="Standalone"
        )

        await team_strategy.add_team_member_permissions(
            team.id, test_user.id, TeamRole.MEMBER
        )

        repo = PermissionRepository(db_session)
        team_permissions = await repo.get_permissions(
            user_id=test_user.id, team_id=team.id
        )
        assert len(team_permissions) == len(role_to_team_permissions(TeamRole.MEMBER))

        project_permissions_1 = await repo.get_permissions(
            user_id=test_user.id, project_id=project1.id
        )
        project_permissions_2 = await repo.get_permissions(
            user_id=test_user.id, project_id=project2.id
        )
        assert project_permissions_1
        assert project_permissions_2
        assert (
            await repo.get_permissions(user_id=test_user.id, project_id=standalone.id)
            == []
        )

        await team_strategy.update_team_member_role_permissions(
            team.id, test_user.id, TeamRole.ADMIN
        )
        updated_team_permissions = await repo.get_permissions(
            user_id=test_user.id, team_id=team.id
        )
        expected = role_to_team_permissions(TeamRole.ADMIN)
        assert all(
            permission.allowed == expected[permission.action]
            for permission in updated_team_permissions
        )

        await team_strategy.remove_team_member_permissions(team.id, test_user.id)
        assert await repo.get_permissions(user_id=test_user.id, team_id=team.id) == []
        assert (
            await repo.get_permissions(user_id=test_user.id, project_id=project1.id)
            == []
        )
        assert (
            await repo.get_permissions(user_id=test_user.id, project_id=standalone.id)
            == []
        )

    async def test_get_user_accessible_teams(
        self,
        team_strategy: TeamRbacStrategy,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        repo = PermissionRepository(db_session)
        await repo.create_permission(
            Permission(
                user_id=test_user.id,
                action=TeamActions.VIEW_TEAM,
                allowed=True,
                team_id=team.id,
            )
        )

        results = await team_strategy.get_user_accessible_teams(
            test_user.id, actions=TeamActions.VIEW_TEAM
        )
        assert [team_item.id for team_item in results] == [team.id]

    async def test_get_user_accessible_teams_excludes_unrelated(
        self,
        team_strategy: TeamRbacStrategy,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        accessible_team = await _create_team(db_session, test_user)
        hidden_team_1 = await _create_team(db_session, test_user_2)
        hidden_team_2 = await _create_team(db_session, test_user_2)

        await _create_project(
            db_session, test_user_2, team=hidden_team_1, name="Hidden Project 1"
        )
        await _create_project(
            db_session, test_user_2, team=hidden_team_2, name="Hidden Project 2"
        )

        repo = PermissionRepository(db_session)
        await repo.create_permission(
            Permission(
                user_id=test_user.id,
                action=TeamActions.VIEW_TEAM,
                allowed=True,
                team_id=accessible_team.id,
            )
        )
        results = await team_strategy.get_user_accessible_teams(
            test_user.id, actions=TeamActions.VIEW_TEAM
        )
        assert {team_item.id for team_item in results} == {accessible_team.id}
