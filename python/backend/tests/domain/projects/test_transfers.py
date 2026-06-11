import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual
from api.routes.service_dependencies import get_scalars_service
from db.database import get_async_session
from domain.projects.controller import router as projects_router
from domain.projects.dto import ProjectOwnerTransferDTO, ProjectTeamTransferDTO
from domain.projects.errors import ProjectPermissionError, ProjectTransferError
from domain.projects.repository import ProjectRepository
from domain.projects.service import ProjectService
from domain.rbac.repository import PermissionRepository
from domain.rbac.permissions.team import TeamActions
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import PermissionChecker
from domain.team.teams.repository import TeamRepository
from domain.team.teams.controller import router as teams_router
from domain.scalars.service import NoOpScalarsService
from models import Project, Role, Team, User


def _service(db: AsyncSession) -> ProjectService:
    project_repository = ProjectRepository(db)
    permission_service = PermissionService(
        db, PermissionRepository(db), project_repository
    )
    return ProjectService(
        db,
        project_repository=project_repository,
        permission_service=permission_service,
        permission_checker=PermissionChecker(db, permission_service),
        team_repository=TeamRepository(db),
    )


async def _project(db: AsyncSession, owner: User, team: Team | None = None) -> Project:
    project = Project(
        name="Transfer project",
        description="",
        owner_id=owner.id,
        team_id=team.id if team else None,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@pytest.fixture
def auth_client(db_session: AsyncSession):
    """Create a project/team API client with configurable authentication."""
    app = FastAPI()
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(teams_router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_scalars_service():
        return NoOpScalarsService()

    app.dependency_overrides[get_async_session] = override_get_db
    app.dependency_overrides[get_scalars_service] = override_scalars_service

    def get_client(user: User) -> TestClient:
        async def override_current_user():
            return user

        app.dependency_overrides[get_current_user_dual] = override_current_user
        return TestClient(app)

    return get_client


class TestProjectTransfers:
    async def test_move_standalone_to_team_preserves_direct_permissions(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = Team(name="Destination", description="", owner_id=test_user_2.id)
        db_session.add(team)
        await db_session.flush()
        project = await _project(db_session, test_user)
        service = _service(db_session)
        await service.permission_service.add_user_to_project_permissions(
            test_user.id, project.id, Role.ADMIN
        )
        await service.permission_service.add_permission(
            test_user.id,
            TeamActions.CREATE_PROJECT,
            team_id=team.id,
        )
        await db_session.commit()

        result = await service.change_project_team(
            test_user, project.id, ProjectTeamTransferDTO(team_id=team.id)
        )

        assert result.team is not None
        assert result.team.id == team.id
        assert result.owner is not None
        assert result.owner.id == test_user_2.id
        direct = await service.permission_service.get_permissions(
            user_id=test_user.id, project_id=project.id
        )
        assert direct.data

    async def test_move_team_to_standalone_does_not_require_source_team_manage(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = Team(name="Source", description="", owner_id=test_user.id)
        db_session.add(team)
        await db_session.flush()
        project = await _project(db_session, test_user, team)
        service = _service(db_session)
        await service.permission_service.add_user_to_project_permissions(
            test_user_2.id, project.id, Role.ADMIN
        )
        await service.permission_service.add_permission(
            test_user_2.id,
            TeamActions.DELETE_PROJECT,
            team_id=team.id,
        )
        await db_session.commit()

        result = await service.change_project_team(
            test_user_2, project.id, ProjectTeamTransferDTO(team_id=None)
        )

        assert result.team is None

    async def test_move_team_to_standalone_requires_source_project_delete(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = Team(name="Source delete", description="", owner_id=test_user.id)
        db_session.add(team)
        await db_session.flush()
        project = await _project(db_session, test_user, team)
        service = _service(db_session)
        await service.permission_service.add_user_to_project_permissions(
            test_user_2.id, project.id, Role.ADMIN
        )
        await db_session.commit()

        with pytest.raises(
            ProjectPermissionError,
            match="remove projects from the source team",
        ):
            await service.change_project_team(
                test_user_2, project.id, ProjectTeamTransferDTO(team_id=None)
            )

    async def test_move_to_team_requires_destination_project_create(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = Team(name="Destination create", description="", owner_id=test_user_2.id)
        db_session.add(team)
        await db_session.flush()
        project = await _project(db_session, test_user)
        service = _service(db_session)
        await service.permission_service.add_user_to_project_permissions(
            test_user.id, project.id, Role.ADMIN
        )
        await db_session.commit()

        with pytest.raises(
            ProjectPermissionError,
            match="create projects in the destination team",
        ):
            await service.change_project_team(
                test_user, project.id, ProjectTeamTransferDTO(team_id=team.id)
            )

    async def test_same_team_request_still_requires_transfer_permissions(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = Team(name="Same team", description="", owner_id=test_user.id)
        db_session.add(team)
        await db_session.flush()
        project = await _project(db_session, test_user, team)
        service = _service(db_session)

        with pytest.raises(ProjectPermissionError):
            await service.change_project_team(
                test_user_2,
                project.id,
                ProjectTeamTransferDTO(team_id=team.id),
            )

    async def test_transfer_standalone_owner_grants_new_owner_and_keeps_old_owner(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        project = await _project(db_session, test_user)
        service = _service(db_session)
        await service.permission_service.add_user_to_project_permissions(
            test_user.id, project.id, Role.ADMIN
        )
        await db_session.commit()

        result = await service.change_project_owner(
            test_user,
            project.id,
            ProjectOwnerTransferDTO(owner_id=test_user_2.id),
        )

        assert result.owner is not None
        assert result.owner.id == test_user_2.id
        old_permissions = await service.permission_service.get_permissions(
            user_id=test_user.id, project_id=project.id
        )
        new_permissions = await service.permission_service.get_permissions(
            user_id=test_user_2.id, project_id=project.id
        )
        assert old_permissions.data
        assert new_permissions.data

    async def test_team_project_owner_cannot_be_changed(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = Team(name="Owned", description="", owner_id=test_user.id)
        db_session.add(team)
        await db_session.flush()
        project = await _project(db_session, test_user, team)
        service = _service(db_session)

        with pytest.raises(ProjectTransferError):
            await service.change_project_owner(
                test_user,
                project.id,
                ProjectOwnerTransferDTO(owner_id=test_user_2.id),
            )


class TestProjectTransferRoutes:
    async def test_owner_can_move_project_and_transfer_standalone_ownership(
        self,
        auth_client,
        test_user: User,
        test_user_2: User,
    ) -> None:
        client = auth_client(test_user)
        team_response = client.post(
            "/api/v1/teams",
            json={"name": "Route destination", "description": ""},
        )
        assert team_response.status_code == 200, team_response.text
        team_id = team_response.json()["id"]
        project_response = client.post(
            "/api/v1/projects",
            json={"name": "Route transfer", "description": ""},
        )
        assert project_response.status_code == 200, project_response.text
        project_id = project_response.json()["id"]

        move_response = client.patch(
            f"/api/v1/projects/{project_id}/team",
            json={"teamId": team_id},
        )
        assert move_response.status_code == 200, move_response.text
        assert move_response.json()["team"]["id"] == team_id

        detach_response = client.patch(
            f"/api/v1/projects/{project_id}/team",
            json={"teamId": None},
        )
        assert detach_response.status_code == 200, detach_response.text
        assert detach_response.json()["team"] is None

        owner_response = client.patch(
            f"/api/v1/projects/{project_id}/owner",
            json={"ownerId": str(test_user_2.id)},
        )
        assert owner_response.status_code == 200, owner_response.text
        assert owner_response.json()["owner"]["id"] == str(test_user_2.id)
