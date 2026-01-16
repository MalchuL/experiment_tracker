from typing import List
from .error import ExperimentNotAccessibleError
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
from .utils import parse_experiment_name
from .mapper import CreateDTOToSchemaProps, ExperimentMapper
from domain.projects.service import ProjectService


class ExperimentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.experiment_repository = ExperimentRepository(db)
        self.project_service = ProjectService(db)
        self.experiment_mapper = ExperimentMapper()

    async def parse_experiment_name(
        self, name: str, pattern: str
    ) -> ExperimentParseResultDTO:
        return self.experiment_mapper.experiment_parse_result_to_dto(
            parse_experiment_name(name, pattern)
        )

    async def parse_experiment_name_from_project(
        self, user: UserProtocol, project_id: UUID_TYPE, name: str
    ) -> ExperimentParseResultDTO:
        project = await self.project_service.get_project_if_accessible(user, project_id)
        if not project:
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        pattern = project.settings.naming_pattern
        return await self.parse_experiment_name(name, pattern)

    async def get_parent_id_if_accessible(
        self, user: UserProtocol, project_id: UUID_TYPE, name: str
    ) -> UUID_TYPE | None:
        """Get parent experiment id if accessible by experiment name"""
        # Get project pattern
        project = await self.project_service.get_project_if_accessible(user, project_id)
        if not project:
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        pattern = project.settings.naming_pattern
        # Get the parent number from the experiment name
        parent_num = (await self.parse_experiment_name(name, pattern)).parent

        # Get all experiments in project
        experiments = await self.experiment_repository.get_experiments_by_project(
            user, project_id
        )
        if not experiments:
            return None

        # Find parent experiment
        for experiment in experiments:
            result = await self.parse_experiment_name(experiment.name, pattern)
            if result.num == parent_num:
                return experiment.id
        return None

    async def get_accessible_experiments(
        self, user: UserProtocol
    ) -> List[ExperimentDTO]:
        experiments = await self.experiment_repository.get_accessible_experiments(user)
        return self.experiment_mapper.experiment_list_schema_to_dto(experiments)

    async def get_recent_experiments(
        self, user: UserProtocol, limit: int = 10
    ) -> List[ExperimentDTO]:
        experiments = await self.experiment_repository.get_accessible_experiments(
            user, ListOptions(limit=limit, offset=0)
        )
        return self.experiment_mapper.experiment_list_schema_to_dto(experiments)

    async def get_experiment_if_accessible(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> ExperimentDTO | None:
        experiment = await self.experiment_repository.get_experiment_if_accessible(
            user, experiment_id
        )
        if not experiment:
            return None
        return self.experiment_mapper.experiment_schema_to_dto(experiment)

    async def create_experiment(
        self, user: UserProtocol, data: ExperimentCreateDTO
    ) -> ExperimentDTO:
        project = await self.project_service.get_project_if_accessible(
            user, data.project_id
        )
        if not project:
            raise ProjectNotAccessibleError(f"Project {data.project_id} not accessible")
        if data.parent_experiment_name:
            parent_id = await self.get_parent_id_if_accessible(
                user,
                data.project_id,
                data.parent_experiment_name,
            )
        else:
            parent_id = None
        props = CreateDTOToSchemaProps(owner_id=user.id, parent_experiment_id=parent_id)
        experiment = self.experiment_mapper.experiment_create_dto_to_schema(data, props)
        await self.experiment_repository.create(experiment)
        await self.experiment_repository.commit()
        experiment = await self.experiment_repository.get_experiment_if_accessible(
            user, experiment.id
        )
        if not experiment:
            raise ExperimentNotAccessibleError(
                f"Experiment {experiment.id} not accessible"
            )
        return self.experiment_mapper.experiment_schema_to_dto(experiment)

    async def update_experiment(
        self, user: UserProtocol, experiment_id: UUID_TYPE, data: ExperimentUpdateDTO
    ) -> ExperimentDTO:
        experiment = await self.experiment_repository.get_experiment_if_accessible(
            user, experiment_id
        )
        if not experiment:
            raise ExperimentNotAccessibleError(
                f"Experiment {experiment_id} not accessible"
            )
        updates = self.experiment_mapper.experiment_update_dto_to_update_dict(data)
        result = await self.experiment_repository.update(experiment_id, **updates)
        await self.experiment_repository.commit()

        return self.experiment_mapper.experiment_schema_to_dto(result)

    async def delete_experiment(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> bool:
        experiment = await self.experiment_repository.get_experiment_if_accessible(
            user, experiment_id
        )
        if not experiment:
            raise ExperimentNotAccessibleError(
                f"Experiment {experiment_id} not accessible"
            )
        await self.experiment_repository.delete(experiment_id)
        await self.experiment_repository.commit()
        return True

    async def reorder_experiments(
        self, user: UserProtocol, project_id: UUID_TYPE, data: List[UUID_TYPE]
    ) -> bool:
        experiments = await self.experiment_repository.get_experiments_by_project(
            user, project_id
        )
        if not experiments:
            raise ExperimentNotAccessibleError(f"Project {project_id} not accessible")
        for i, experiment_id in enumerate(data):
            await self.experiment_repository.update(experiment_id, order=i)
        await self.experiment_repository.commit()
        return True
