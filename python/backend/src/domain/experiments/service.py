from typing import List

from .error import ExperimentNotAccessibleError
from lib.pagination import ListOptions
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import ExperimentRepository
from .dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentListResponseDTO,
    ExperimentUpdateDTO,
)
from .mapper import ExperimentMapper
from domain.rbac.wrapper import PermissionChecker


class ExperimentService:
    def __init__(
        self,
        db: AsyncSession,
        experiment_repository: ExperimentRepository,
        permission_checker: PermissionChecker,
    ):
        self.db = db
        self.experiment_repository = experiment_repository
        self.permission_checker = permission_checker
        self.experiment_mapper = ExperimentMapper()

    async def get_recent_experiments(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(limit=10, offset=0),
    ) -> ExperimentListResponseDTO:
        if not await self.permission_checker.can_view_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to view experiments in project {project_id}"
            )
        experiments_page = await self.experiment_repository.get_latest_experiments(
            project_id, list_options
        )
        return ExperimentListResponseDTO.from_page(
            experiments_page.map(
                self.experiment_mapper.experiment_schema_to_dto
            )
        )

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
        if data.parent_experiment_id:
            parent_id = data.parent_experiment_id
            experiment = await self.experiment_repository.get_by_id(parent_id)
            if not experiment:
                raise ExperimentNotAccessibleError(
                    f"Parent experiment {parent_id} not found"
                )
            if experiment.project_id != data.project_id:
                raise ExperimentNotAccessibleError(
                    f"Parent experiment {parent_id} not in project {data.project_id}"
                )

        experiment = self.experiment_mapper.experiment_create_dto_to_schema(data)
        await self.experiment_repository.create(experiment)
        await self.db.commit()
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
        await self.db.commit()

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
        await self.db.commit()
        return True

    async def reorder_experiments(
        self, user: UserProtocol, project_id: UUID_TYPE, data: List[UUID_TYPE]
    ) -> bool:
        if not await self.permission_checker.can_edit_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to edit experiments in project {project_id}"
            )
        experiments = (
            await self.experiment_repository.get_experiments_by_project(project_id)
        ).data
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
        await self.db.commit()
        return True

    async def get_experiments_by_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(),
    ) -> ExperimentListResponseDTO:
        if not await self.permission_checker.can_view_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to view experiments in project {project_id}"
            )
        experiments_page = await self.experiment_repository.get_experiments_by_project(
            project_id,
            list_options=list_options,
        )
        return ExperimentListResponseDTO.from_page(
            experiments_page.map(
                self.experiment_mapper.experiment_schema_to_dto
            )
        )
