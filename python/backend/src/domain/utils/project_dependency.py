from fastapi import Depends

from domain.projects.dependencies import get_project_repository, get_project_service
from domain.projects.dto import (
    ProjectDataDTO,
    ProjectMetricDTO,
    ProjectSettingsDTO,
)
from domain.projects.errors import ProjectNotAccessibleError
from domain.projects.repository import ProjectRepository
from domain.projects.service import ProjectService
from domain.rbac.permissions.project import ProjectActions
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from models import Project


async def get_project_if_accessible(
    user: UserProtocol,
    project_id: UUID_TYPE,
    actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    full_load: bool = True,
    project_service: ProjectService = Depends(get_project_service),
    project_repository: ProjectRepository = Depends(get_project_repository),
) -> Project:
    if await project_service.is_user_accessible_project(user, project_id, actions=actions):
        project = await project_repository.get_project_by_id(
            project_id, full_load=full_load
        )
        if not project:
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        return project
    raise ProjectNotAccessibleError(f"Project {project_id} not accessible")


async def get_project_dto_if_accessible(
    user: UserProtocol,
    project_id: UUID_TYPE,
    actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    full_load: bool = True,
    project_service: ProjectService = Depends(get_project_service),
    project_repository: ProjectRepository = Depends(get_project_repository),
) -> ProjectDataDTO | None:
    if not await project_service.is_user_accessible_project(
        user, project_id, actions=actions
    ):
        return None
    project_model = await project_repository.get_project_by_id(
        project_id, full_load=full_load
    )
    return ProjectDataDTO(
        id=project_model.id,
        name=project_model.name,
        description=project_model.description,
        metrics=[ProjectMetricDTO.model_validate(metric) for metric in project_model.metrics],
        settings=ProjectSettingsDTO.model_validate(project_model.settings),
        team_id=project_model.team_id,
        owner_id=project_model.owner_id,
    )
