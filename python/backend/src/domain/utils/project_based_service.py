from abc import ABC
from domain.projects.dto import (
    ProjectBaseDTO,
    ProjectDataDTO,
    ProjectMetricDTO,
    ProjectSettingsDTO,
)
from domain.rbac.permissions.project import ProjectActions
from models import Project
from domain.projects.errors import ProjectNotAccessibleError
from domain.projects.repository import ProjectRepository
from domain.rbac.wrapper import PermissionChecker
from domain.projects.service import ProjectService
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession


class ProjectBasedService(ABC):
    def __init__(self, db: AsyncSession):
        self._project_service = ProjectService(db)
        self._project_repository = self._project_service.project_repository
        self._permission_checker = PermissionChecker(db)

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
        if not await self._project_service.is_user_accessible_project(
            user, project_id, actions=actions
        ):
            return None
        project_model = await self._project_repository.get_project_by_id(
            project_id, full_load=full_load
        )
        return ProjectDataDTO(
            id=project_model.id,
            name=project_model.name,
            description=project_model.description,
            metrics=[
                ProjectMetricDTO.model_validate(metric)
                for metric in project_model.metrics
            ],
            settings=ProjectSettingsDTO.model_validate(project_model.settings),
            team_id=project_model.team_id,
            owner_id=project_model.owner_id,
        )
