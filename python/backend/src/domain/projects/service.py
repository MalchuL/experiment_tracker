from typing import List
from domain.projects.repository import ProjectRepository
from domain.projects.mapper import (
    CreateDTOToSchemaProps,
    ProjectMapper,
    SchemaToDTOProps,
)
from domain.projects.errors import ProjectNotAccessibleError, ProjectPermissionError
from domain.rbac.permissions import ProjectActions, TeamActions
from domain.rbac.service import PermissionService
from lib.dto_converter import DtoConverter
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession
from domain.projects.dto import ProjectDTO, ProjectCreateDTO, ProjectUpdateDTO
from models import Role


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repository = ProjectRepository(db)
        self.permission_service = PermissionService(db, auto_commit=False)
        self.project_mapper = ProjectMapper()

    async def create_project(
        self, user: UserProtocol, data: ProjectCreateDTO
    ) -> ProjectDTO:
        try:
            props = CreateDTOToSchemaProps(owner_id=user.id)
            if data.team_id and not await self.permission_service.has_permission(
                user_id=user.id,
                team_id=data.team_id,
                action=TeamActions.CREATE_PROJECT,
            ):
                raise ProjectNotAccessibleError(
                    f"Project {data.team_id} not accessible"
                )
            project_model = self.project_mapper.project_create_dto_to_schema(
                data, props
            )
            await self.project_repository.create(project_model)
            if not data.team_id:
                await self.permission_service.add_user_to_project_permissions(
                    user.id, project_model.id, Role.ADMIN
                )
            await self.project_repository.commit()
        except Exception as e:
            await self.project_repository.rollback()
            raise e
        # When creating a project, the counts are 0
        props = SchemaToDTOProps(
            experiment_count=0,
            hypothesis_count=0,
        )
        project_model = await self.project_repository.get_project_if_accessible(
            user, project_model.id
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
            project_model = await self.project_repository.get_project_if_accessible(
                user, project_id
            )
            if not project_model:
                raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
            # Check if the user has permission to update the project
            if (
                project_model.team_id
                and not await self.permission_service.has_permission(
                    user_id=user.id,
                    team_id=project_model.team_id,
                    action=TeamActions.CREATE_PROJECT,
                )
            ):
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to update project {project_id}"
                )
            # Update the project in the repository
            await self.project_repository.update(project_id, **update_dict)
            await self.project_repository.commit()
            # TODO check if this is needed, maybe update another way?
            # Fetch the updated project with relationships loaded
            updated_project = await self.project_repository.get_project_if_accessible(
                user, project_id
            )
            if not updated_project:
                raise ProjectNotAccessibleError(
                    f"Project {project_id} not found or not accessible"
                )

            # Convert to DTO with counts
            experiment_count = (
                len(updated_project.experiments) if updated_project.experiments else 0
            )
            hypothesis_count = (
                len(updated_project.hypotheses) if updated_project.hypotheses else 0
            )
            props = SchemaToDTOProps(
                experiment_count=experiment_count, hypothesis_count=hypothesis_count
            )
            return self.project_mapper.project_schema_to_dto(updated_project, props)
        except Exception as e:
            await self.project_repository.rollback()
            raise e

    async def get_accessible_projects(
        self,
        user: UserProtocol,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    ) -> List[ProjectDTO]:
        project_models = await self.project_repository.get_accessible_projects(
            user, actions=actions
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
        project_model = await self.project_repository.get_project_if_accessible(
            user, project_id, actions=actions
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
        return await self.project_repository.is_user_accessible_project(
            user, project_id, actions=actions
        )

    async def delete_project(self, user: UserProtocol, project_id: UUID_TYPE) -> bool:
        try:
            project_model = await self.project_repository.get_by_id(project_id)
            if not project_model:
                raise ProjectNotAccessibleError(f"Project {project_id} not found")
            if project_model.owner_id != user.id:
                raise ProjectPermissionError(
                    f"User {user.id} does not have permission to delete project {project_id}"
                )
            await self.project_repository.delete(project_id)
            await self.project_repository.commit()
            return True
        except Exception as e:
            await self.project_repository.rollback()
            raise e
