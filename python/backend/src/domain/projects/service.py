from typing import List
from domain.projects.repository import ProjectRepository
from domain.projects.mapper import (
    CreateDTOToSchemaProps,
    ProjectMapper,
    SchemaToDTOProps,
)
from domain.projects.errors import ProjectNotAccessibleError, ProjectPermissionError
from lib.db.error import DBNotFoundError
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import PermissionChecker
from lib.dto_converter import DtoConverter
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession
from domain.projects.dto import ProjectDTO, ProjectCreateDTO, ProjectUpdateDTO
from models import Role
from domain.team.teams.repository import TeamRepository
from domain.scalars.service import NoOpScalarsService, ScalarsServiceProtocol


class ProjectService:
    def __init__(
        self,
        db: AsyncSession,
        scalars_service: ScalarsServiceProtocol | None = None,
    ):
        self.db = db
        self.project_repository = ProjectRepository(db)
        self.permission_service = PermissionService(db, auto_commit=False)
        self.permission_checker = PermissionChecker(db)
        self.team_repository = TeamRepository(db)
        self.project_mapper = ProjectMapper()
        self.scalars_service = scalars_service or NoOpScalarsService()

    async def get_accessible_project_ids(
        self, user: UserProtocol, actions: list[str] | str | None
    ) -> list[UUID_TYPE]:
        permission_project_ids = (
            await self.permission_service.get_user_accessible_project_ids(
                user.id, actions=actions
            )
        )
        return list(permission_project_ids)

    async def create_project(
        self, user: UserProtocol, data: ProjectCreateDTO
    ) -> ProjectDTO:
        try:
            # Check if the user is allowed to create a project in the team
            if data.team_id and not await self.permission_checker.can_create_project(
                user.id, data.team_id
            ):
                raise ProjectNotAccessibleError(
                    f"You are not allowed to create a project in team {data.team_id}"
                )
            if data.team_id:
                team = await self.team_repository.get_by_id(data.team_id)
                props = CreateDTOToSchemaProps(owner_id=team.owner_id)
            else:
                props = CreateDTOToSchemaProps(owner_id=user.id)
            project_model = self.project_mapper.project_create_dto_to_schema(
                data, props
            )
            await self.project_repository.create(project_model)
            # If the project is not in a team, add the user to the project permissions
            if not data.team_id:
                await self.permission_service.add_user_to_project_permissions(
                    user.id, project_model.id, Role.ADMIN
                )
            await self.scalars_service.create_project_table(str(project_model.id))
            await self.project_repository.commit()
        except Exception as e:
            await self.project_repository.rollback()
            raise e
        # When creating a project, the counts are 0
        props = SchemaToDTOProps(
            experiment_count=0,
            hypothesis_count=0,
        )
        created_project_id = project_model.id
        project_model = await self.project_repository.get_project_by_id(
            created_project_id, full_load=True
        )
        return self.project_mapper.project_schema_to_dto(
            project_model,
            props,
        )

    async def update_project(
        self, user: UserProtocol, project_id: UUID_TYPE, data: ProjectUpdateDTO
    ) -> ProjectDTO:
        """Update a project with partial data from ProjectUpdateDTO"""
        try:
            # Convert DTO to update dictionary
            update_dict = self.project_mapper.project_update_dto_to_update_dict(data)
            try:
                project_model = await self.project_repository.get_by_id(project_id)
            except DBNotFoundError:
                raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
            if not await self.permission_checker.can_edit_project(user.id, project_id):
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to update project {project_id}"
                )
            # TODO: Update metrics and settings if they are provided in the update dictionary
            # Now this doesn't support for partial updates of metrics and settings (also in mapper).
            # Update the project in the repository
            updated_project = await self.project_repository.update(
                project_id, **update_dict
            )
            updated_project = await self.project_repository.get_project_by_id(
                project_id, full_load=True
            )
            await self.project_repository.commit()
            return self.project_mapper.project_schema_to_dto(
                updated_project,
                SchemaToDTOProps(
                    experiment_count=len(updated_project.experiments),
                    hypothesis_count=len(updated_project.hypotheses),
                ),
            )
        except Exception as e:
            await self.project_repository.rollback()
            raise e

    async def get_accessible_projects(
        self,
        user: UserProtocol,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    ) -> List[ProjectDTO]:
        project_ids = await self.get_accessible_project_ids(user, actions)
        if not project_ids:
            return []
        project_models = await self.project_repository.get_projects_by_ids(
            project_ids, full_load=True
        )
        experiment_counts = [
            len(project.experiments) if project.experiments else 0
            for project in project_models
        ]
        hypothesis_counts = [
            len(project.hypotheses) if project.hypotheses else 0
            for project in project_models
        ]
        props = [
            SchemaToDTOProps(
                experiment_count=experiment_count, hypothesis_count=hypothesis_count
            )
            for experiment_count, hypothesis_count in zip(
                experiment_counts, hypothesis_counts
            )
        ]
        return self.project_mapper.project_list_schema_to_dto(project_models, props)

    async def get_project_if_accessible(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    ) -> ProjectDTO | None:
        if not await self.is_user_accessible_project(user, project_id, actions=actions):
            return None
        project_model = await self.project_repository.get_project_by_id(
            project_id, full_load=True
        )
        if not project_model:
            return None
        experiment_count = (
            len(project_model.experiments) if project_model.experiments else 0
        )
        hypothesis_count = (
            len(project_model.hypotheses) if project_model.hypotheses else 0
        )
        props = SchemaToDTOProps(
            experiment_count=experiment_count, hypothesis_count=hypothesis_count
        )
        return self.project_mapper.project_schema_to_dto(project_model, props)

    async def is_user_accessible_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    ) -> bool:
        if actions is None:
            actions = ProjectActions.VIEW_PROJECT
        actions_list = [actions] if isinstance(actions, str) else actions
        return await self.permission_service.has_permission(
            user_id=user.id, project_id=project_id, actions=actions_list
        )

    # TODO: Delete the project from the scalars service
    async def delete_project(self, user: UserProtocol, project_id: UUID_TYPE) -> bool:
        try:
            if not await self.permission_checker.can_delete_project(
                user.id, project_id
            ):
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to delete project {project_id}"
                )
            await self.project_repository.delete(project_id)
            await self.project_repository.commit()
            return True
        except Exception as e:
            await self.project_repository.rollback()
            raise e
