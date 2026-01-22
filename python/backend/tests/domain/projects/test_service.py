from uuid import uuid4

from lib.db.error import DBNotFoundError
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.dto import ProjectCreateDTO, ProjectUpdateDTO
from domain.projects.errors import ProjectNotAccessibleError, ProjectPermissionError
from domain.projects.service import ProjectService
from domain.rbac.permissions.project import ProjectActions, role_to_project_permissions
from domain.rbac.permissions.team import TeamActions
from domain.rbac.repository import PermissionRepository
from domain.rbac.service import PermissionService
from domain.team.teams.dto import TeamCreateDTO, TeamMemberCreateDTO
from domain.team.teams.service import TeamService
from models import Project, Role, Team, User


async def _create_team(
    db_session: AsyncSession, owner: User, name: str = "Project Service Team"
) -> Team:
    team = Team(
        id=None,
        name=name,
        description="Team for project service tests",
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
    name: str = "Project Service",
) -> Project:
    team_id = team.id if team is not None else None
    project = Project(
        id=None,
        name=name,
        description="Project service test",
        owner_id=owner.id,
        team_id=team_id,
        metrics=[],
        settings={},
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


class TestProjectService:
    @pytest.fixture
    def project_service(self, db_session: AsyncSession) -> ProjectService:
        return ProjectService(db_session)

    async def test_create_project_without_team_adds_permissions(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        dto = ProjectCreateDTO(name="Solo Project", description="Solo description")

        created = await project_service.create_project(test_user, dto)

        assert created.id is not None
        assert created.owner.id == test_user.id
        assert created.team is None
        assert created.experiment_count == 0
        assert created.hypothesis_count == 0

        permission_repo = PermissionRepository(db_session)
        permissions = await permission_repo.get_permissions(
            user_id=test_user.id, project_id=created.id
        )
        permissions_map = {item.action: item.allowed for item in permissions}
        assert permissions_map == role_to_project_permissions(Role.ADMIN)

    async def test_create_project_in_team_requires_permission(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        dto = ProjectCreateDTO(
            name="Team Project", description="Team description", team_id=team.id
        )

        with pytest.raises(ProjectNotAccessibleError):
            await project_service.create_project(test_user, dto)

    async def test_create_project_in_team_does_not_add_project_permissions(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.CREATE_PROJECT,
            allowed=True,
            team_id=team.id,
        )
        dto = ProjectCreateDTO(
            name="Team Project", description="Team description", team_id=team.id
        )

        created = await project_service.create_project(test_user, dto)

        permission_repo = PermissionRepository(db_session)
        permissions = await permission_repo.get_permissions(
            user_id=test_user.id, project_id=created.id
        )
        assert permissions == []

    async def test_update_project_permission_denied(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        dto = ProjectUpdateDTO(name="Denied Update", description=None)

        with pytest.raises(ProjectPermissionError):
            await project_service.update_project(test_user, project.id, dto)

    async def test_update_project_missing_raises(
        self, project_service: ProjectService, test_user: User
    ) -> None:
        dto = ProjectUpdateDTO(name="Missing", description=None)

        with pytest.raises(ProjectNotAccessibleError):
            await project_service.update_project(test_user, uuid4(), dto)

    async def test_update_project_updates_fields(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.EDIT_PROJECT,
            allowed=True,
            project_id=project.id,
        )
        dto = ProjectUpdateDTO(name="Updated", description="Updated description")

        updated = await project_service.update_project(test_user, project.id, dto)

        assert updated.id == project.id
        assert updated.name == "Updated"
        assert updated.description == "Updated description"

    async def test_get_accessible_projects_includes_team_and_project_permissions(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        team_project = await _create_project(
            db_session, test_user, team=team, name="Team Project"
        )
        standalone_project = await _create_project(
            db_session, test_user, team=None, name="Standalone Project"
        )
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_PROJECTS,
            allowed=True,
            team_id=team.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=standalone_project.id,
        )

        projects = await project_service.get_accessible_projects(
            test_user,
            actions=[ProjectActions.VIEW_PROJECT, TeamActions.VIEW_PROJECTS],
        )

        project_ids = {project.id for project in projects}
        assert project_ids == {team_project.id, standalone_project.id}
        for project in projects:
            assert project.experiment_count == 0
            assert project.hypothesis_count == 0

    async def test_get_project_if_accessible_returns_none_without_access(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        result = await project_service.get_project_if_accessible(test_user, project.id)

        assert result is None

    async def test_get_project_if_accessible_returns_project_with_permission(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )

        result = await project_service.get_project_if_accessible(test_user, project.id)
        assert (
            await project_service.is_user_accessible_project(
                test_user,
                project.id,
                actions=ProjectActions.CREATE_EXPERIMENT,
            )
            == False
        )
        assert (
            await project_service.is_user_accessible_project(
                test_user,
                project.id,
                actions=ProjectActions.VIEW_PROJECT,
            )
            == True
        )

        assert result is not None
        assert result.id == project.id

    async def test_is_user_accessible_project_any_action_succeeds(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )

        allowed = await project_service.is_user_accessible_project(
            test_user,
            project.id,
            actions=[ProjectActions.EDIT_PROJECT, ProjectActions.VIEW_PROJECT],
        )

        assert allowed is True
        with pytest.raises(DBNotFoundError):
            assert (
                await project_service.is_user_accessible_project(
                    test_user, uuid4(), actions=ProjectActions.VIEW_PROJECT
                )
                is False
            )

    async def test_delete_project_permission_denied(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        with pytest.raises(ProjectPermissionError):
            await project_service.delete_project(test_user, project.id)

    async def test_delete_project_removes_project(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.DELETE_PROJECT,
            allowed=True,
            project_id=project.id,
        )

        deleted = await project_service.delete_project(test_user, project.id)

        assert deleted is True
        assert await db_session.get(Project, project.id) is None

    async def test_team_service_owner_can_create_team_project(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team_service = TeamService(db_session)
        team = await team_service.create_team(
            test_user.id, TeamCreateDTO(name="Owner Team", description="Owned")
        )
        dto = ProjectCreateDTO(
            name="Owner Project", description="Owned project", team_id=team.id
        )

        created = await project_service.create_project(test_user, dto)

        assert created.team is not None
        assert created.team.id == team.id

    async def test_team_service_admin_can_delete_team_project(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team_service = TeamService(db_session)
        team = await team_service.create_team(
            test_user.id, TeamCreateDTO(name="Admin Team", description="Admin owned")
        )
        await team_service.add_team_member(
            test_user.id,
            TeamMemberCreateDTO(
                user_id=test_user_2.id, team_id=team.id, role=Role.ADMIN
            ),
        )
        dto = ProjectCreateDTO(
            name="Admin Project", description="Admin project", team_id=team.id
        )
        created = await project_service.create_project(test_user, dto)

        deleted = await project_service.delete_project(test_user_2, created.id)

        assert deleted is True
        assert await db_session.get(Project, created.id) is None

    async def test_team_service_member_can_view_team_projects(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team_service = TeamService(db_session)
        team = await team_service.create_team(
            test_user.id, TeamCreateDTO(name="Member Team", description="Members")
        )
        await team_service.add_team_member(
            test_user.id,
            TeamMemberCreateDTO(
                user_id=test_user_2.id, team_id=team.id, role=Role.MEMBER
            ),
        )
        dto = ProjectCreateDTO(
            name="Member Project", description="Member project", team_id=team.id
        )
        team_project = await project_service.create_project(test_user, dto)

        projects = await project_service.get_accessible_projects(
            test_user_2, actions=ProjectActions.VIEW_PROJECT
        )

        project_ids = {project.id for project in projects}
        assert team_project.id in project_ids
