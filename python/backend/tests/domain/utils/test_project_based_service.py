import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.dto import ProjectBaseDTO
from domain.projects.errors import ProjectNotAccessibleError
from domain.rbac.permissions.project import ProjectActions
from domain.rbac.service import PermissionService
from domain.utils.project_based_service import ProjectBasedService
from models import Project, User


class ConcreteProjectBasedService(ProjectBasedService):
    """Concrete wrapper to exercise ProjectBasedService helpers."""


async def _create_project(
    db_session: AsyncSession,
    owner: User,
    name: str = "Project Based",
    metrics: list[dict] | None = None,
    settings: dict | None = None,
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Project based service test",
        owner_id=owner.id,
        team_id=None,
        metrics=metrics or [],
        settings=settings or {},
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


class TestProjectBasedService:
    @pytest.fixture
    def project_based_service(self, db_session: AsyncSession) -> ProjectBasedService:
        return ConcreteProjectBasedService(db_session)

    async def test_get_project_if_accessible_returns_project(
        self,
        project_based_service: ProjectBasedService,
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

        loaded = await project_based_service._get_project_if_accessible(
            test_user, project.id
        )

        assert loaded.id == project.id

    async def test_get_project_if_accessible_denies_without_permission(
        self,
        project_based_service: ProjectBasedService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        with pytest.raises(ProjectNotAccessibleError):
            await project_based_service._get_project_if_accessible(
                test_user, project.id
            )

    async def test_get_project_dto_if_accessible_returns_none_when_denied(
        self,
        project_based_service: ProjectBasedService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        result = await project_based_service._get_project_dto_if_accessible(
            test_user, project.id, actions=ProjectActions.VIEW_PROJECT
        )

        assert result is None

    async def test_get_project_dto_if_accessible_returns_dto(
        self,
        project_based_service: ProjectBasedService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        metrics = [
            {
                "name": "accuracy",
                "direction": "minimize",
                "aggregation": "last",
            }
        ]
        settings = {
            "naming_pattern": "{num}_from_{parent}_{change}",
            "display_metrics": ["accuracy"],
        }
        project = await _create_project(
            db_session,
            test_user,
            metrics=metrics,
            settings=settings,
        )
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )

        result = await project_based_service._get_project_dto_if_accessible(
            test_user, project.id, actions=ProjectActions.VIEW_PROJECT
        )

        assert isinstance(result, ProjectBaseDTO)
        assert result.name == project.name
        assert result.description == project.description
        assert len(result.metrics) == 1
        assert result.metrics[0].name == "accuracy"
        assert result.settings.naming_pattern == settings["naming_pattern"]
        assert result.settings.display_metrics == settings["display_metrics"]
