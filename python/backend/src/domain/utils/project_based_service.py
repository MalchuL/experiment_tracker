from abc import ABC
from domain.projects.dto import (
    ProjectDataDTO,
)
from domain.rbac.permissions.project import ProjectActions
from models import Project
from domain.projects.errors import ProjectNotAccessibleError
from domain.projects.repository import ProjectRepository
from domain.rbac.repository import PermissionRepository
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import PermissionChecker
from domain.projects.service import ProjectService
from domain.team.teams.repository import TeamRepository
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession


class ProjectBasedService(ABC):
    def __init__(self, db: AsyncSession):
        self._project_repository = ProjectRepository(db)
        self._permission_service = PermissionService(
            db, PermissionRepository(db), self._project_repository
        )
        self._permission_checker = PermissionChecker(db, self._permission_service)
        self._project_service = ProjectService(
            db=db,
            project_repository=self._project_repository,
            permission_service=self._permission_service,
            permission_checker=self._permission_checker,
            team_repository=TeamRepository(db),
        )

    async def _get_project_if_accessible(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
        full_load: bool = True,
    ) -> Project:

        if await self._project_service.is_user_accessible_project(
            user, project_id, actions=actions
        ):
            project = await self._project_repository.get_project_by_id(
                project_id, full_load=full_load
            )
            if not project:
                raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
            return project
        raise ProjectNotAccessibleError(f"Project {project_id} not accessible")

    async def _get_project_dto_if_accessible(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
        full_load: bool = True,
    ) -> ProjectDataDTO:
        project_dto = await self._project_service.get_project_if_accessible(
            user, project_id, actions=actions
        )
        if not project_dto:
            return None
        return ProjectDataDTO(
            id=project_dto.id,
            name=project_dto.name,
            description=project_dto.description,
            metrics=project_dto.metrics,
            settings=project_dto.settings,
            team_id=project_dto.team.id if project_dto.team else None,
            owner_id=project_dto.owner.id,
        )
