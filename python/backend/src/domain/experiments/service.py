from turtle import update
from typing import List

from domain.projects.dto import ProjectDTO, ProjectDataDTO
from models import Project
from .error import ExperimentNamePatternNotSetError, ExperimentNotAccessibleError
from domain.projects.errors import ProjectNotAccessibleError
from lib.db.base_repository import ListOptions
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import ExperimentRepository
from .dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentParseResultDTO,
    ExperimentUpdateDTO,
)
from .utils import DEFAULT_EXPERIMENT_NAME_PATTERN, parse_experiment_name
from .mapper import CreateDTOToSchemaProps, ExperimentMapper
from domain.projects.service import ProjectService
from domain.rbac.permissions import ProjectActions
from domain.rbac.wrapper import PermissionChecker
from lib.db.error import DBNotFoundError
from domain.projects.repository import ProjectRepository
from domain.utils.project_based_service import ProjectBasedService


class ExperimentService(ProjectBasedService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.experiment_repository = ExperimentRepository(db)
        self.experiment_mapper = ExperimentMapper()
        self.permission_checker = PermissionChecker(db)

    def _get_project_naming_pattern(self, project: ProjectDataDTO) -> str:
        settings = project.settings or {}
        if hasattr(settings, "naming_pattern"):
            return settings.naming_pattern
        if isinstance(settings, dict):
            if "naming_pattern" in settings:
                return settings["naming_pattern"]
        raise ExperimentNamePatternNotSetError(
            f"Project {project.id} has no naming pattern"
        )

    async def parse_experiment_name(
        self, name: str, pattern: str
    ) -> ExperimentParseResultDTO:
        return self.experiment_mapper.experiment_parse_result_to_dto(
            parse_experiment_name(name, pattern, raise_error=False)
        )

    # TODO add several patterns support to select which one to use
    async def parse_experiment_name_from_project(
        self, user: UserProtocol, project_id: UUID_TYPE, name: str
    ) -> ExperimentParseResultDTO:
        project = await self._get_project_if_accessible(
            user, project_id, ProjectActions.VIEW_EXPERIMENT
        )
        pattern = self._get_project_naming_pattern(project)
        return await self.parse_experiment_name(name, pattern)

    # TODO cover with tests
    # TODO For parent name must be used full name
    async def get_parent_id_if_accessible(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        name: str | None = None,
        parent_name: str | None = None,
    ) -> UUID_TYPE | None:
        """Get parent experiment id if accessible by experiment name"""
        # Get project pattern
        project = await self._get_project_if_accessible(
            user, project_id, ProjectActions.VIEW_EXPERIMENT
        )
        pattern = self._get_project_naming_pattern(project)
        # Get the parent number from the experiment name
        if name:
            parent_num = (await self.parse_experiment_name(name, pattern)).parent
        elif parent_name:
            parent_num = (await self.parse_experiment_name(parent_name, pattern)).num
        else:
            return None

        if not parent_num:
            return None

        # Get all experiments in project
        experiments = await self.experiment_repository.get_experiments_by_project(
            project_id
        )
        if not experiments:
            return None

        # Find parent experiment
        for experiment in experiments:
            result = await self.parse_experiment_name(experiment.name, pattern)
            if result.num and result.num == parent_num:
                return experiment.id
        return None

    async def get_recent_experiments(
        self, user: UserProtocol, limit: int = 10
    ) -> List[ExperimentDTO]:
        experiments = await self.experiment_repository.get_user_experiments(
            user, ListOptions(limit=limit, offset=0)
        )
        return self.experiment_mapper.experiment_list_schema_to_dto(experiments)

    async def get_experiment_if_accessible(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> ExperimentDTO | None:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        if not await self.permission_checker.can_view_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"Experiment {experiment_id} not accessible"
            )
        return self.experiment_mapper.experiment_schema_to_dto(experiment)

    async def create_experiment(
        self, user: UserProtocol, data: ExperimentCreateDTO
    ) -> ExperimentDTO:
        if not await self.permission_checker.can_create_experiment(
            user.id, data.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to create an experiment in project {data.project_id}"
            )
        if data.parent_experiment_name:
            # If parent experiment name is provided, use it to get the parent id
            parent_id = await self.get_parent_id_if_accessible(
                user,
                data.project_id,
                parent_name=data.parent_experiment_name,
            )
        else:
            # TODO cover with tests
            # Else try to get the parent id from the experiment name
            parent_id = await self.get_parent_id_if_accessible(
                user,
                data.project_id,
                name=data.name,
            )
        props = CreateDTOToSchemaProps(owner_id=user.id, parent_experiment_id=parent_id)
        experiment = self.experiment_mapper.experiment_create_dto_to_schema(data, props)
        await self.experiment_repository.create(experiment)
        await self.experiment_repository.commit()
        return self.experiment_mapper.experiment_schema_to_dto(experiment)

    async def update_experiment(
        self, user: UserProtocol, experiment_id: UUID_TYPE, data: ExperimentUpdateDTO
    ) -> ExperimentDTO:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        if not await self.permission_checker.can_edit_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to edit experiment {experiment_id}"
            )
        updates = self.experiment_mapper.experiment_update_dto_to_update_dict(data)
        result = await self.experiment_repository.update(experiment_id, **updates)
        await self.experiment_repository.commit()

        return self.experiment_mapper.experiment_schema_to_dto(result)

    async def delete_experiment(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> bool:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        if not await self.permission_checker.can_delete_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to delete experiment {experiment_id}"
            )
        await self.experiment_repository.delete(experiment_id)
        await self.experiment_repository.commit()
        return True

    async def reorder_experiments(
        self, user: UserProtocol, project_id: UUID_TYPE, data: List[UUID_TYPE]
    ) -> bool:
        if not await self.permission_checker.can_edit_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to edit experiments in project {project_id}"
            )
        experiments = await self.experiment_repository.get_experiments_by_project(
            project_id
        )
        for i, experiment_id in enumerate(data):
            experiment = next(
                (e for e in experiments if str(e.id) == str(experiment_id)), None
            )
            if not experiment:
                raise ExperimentNotAccessibleError(
                    f"Experiment {experiment_id} not found in project {project_id}"
                )
            if not await self.permission_checker.can_edit_experiment(
                user.id, experiment.project_id
            ):
                raise ExperimentNotAccessibleError(
                    f"You are not allowed to edit experiment {experiment_id}"
                )
            await self.experiment_repository.update(experiment_id, order=i)
        await self.experiment_repository.commit()
        return True

    async def get_experiments_by_project(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> List[ExperimentDTO]:
        if not await self.permission_checker.can_view_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to view experiments in project {project_id}"
            )
        experiments = await self.experiment_repository.get_experiments_by_project(
            project_id
        )
        return self.experiment_mapper.experiment_list_schema_to_dto(experiments)
