from typing import List

from domain.projects.errors import ProjectNotAccessibleError
from domain.projects.service import ProjectService
from domain.rbac.permissions import ProjectActions
from domain.rbac.wrapper import PermissionChecker
from domain.utils.project_based_service import ProjectBasedService
from lib.db.base_repository import DBNotFoundError, ListOptions
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession

from .dto import HypothesisCreateDTO, HypothesisDTO, HypothesisUpdateDTO
from .error import HypothesisNotAccessibleError, HypothesisNotFoundError
from .mapper import HypothesisMapper
from .repository import HypothesisRepository


class HypothesisService(ProjectBasedService):
    def __init__(self, db: AsyncSession):
        self.db = db
        self.hypothesis_repository = HypothesisRepository(db)
        self.project_service = ProjectService(db)
        self.hypothesis_mapper = HypothesisMapper()
        self.permission_checker = PermissionChecker(db)

    async def get_accessible_hypotheses(
        self, user: UserProtocol
    ) -> List[HypothesisDTO]:
        hypotheses = await self.hypothesis_repository.get_accessible_hypotheses(user)
        return self.hypothesis_mapper.hypothesis_list_schema_to_dto(hypotheses)

    async def get_hypotheses_by_project(
        self, user: UserProtocol, project_id: UUID_TYPE, limit: int | None = None
    ) -> List[HypothesisDTO]:
        if not await self.permission_checker.can_view_hypothesis(user.id, project_id):
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        hypotheses = await self.hypothesis_repository.get_hypotheses_by_project(
            project_id, limit
        )
        return self.hypothesis_mapper.hypothesis_list_schema_to_dto(hypotheses)

    async def get_hypothesis_if_accessible(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE
    ) -> HypothesisDTO:
        try:
            hypothesis = await self.hypothesis_repository.get_by_id(hypothesis_id)
            if not hypothesis:
                raise HypothesisNotFoundError(f"Hypothesis {hypothesis_id} not found")
        except DBNotFoundError:
            raise HypothesisNotFoundError(f"Hypothesis {hypothesis_id} not found")
        if await self.permission_checker.can_view_hypothesis(
            user.id, hypothesis.project_id
        ):
            return self.hypothesis_mapper.hypothesis_schema_to_dto(hypothesis)
        raise HypothesisNotAccessibleError(f"Hypothesis {hypothesis_id} not accessible")

    async def create_hypothesis(
        self, user: UserProtocol, data: HypothesisCreateDTO
    ) -> HypothesisDTO:
        if not await self.permission_checker.can_create_hypothesis(
            user.id, data.project_id
        ):
            raise HypothesisNotAccessibleError(
                f"Project {data.project_id} not accessible"
            )
        hypothesis = self.hypothesis_mapper.hypothesis_create_dto_to_schema(data)
        await self.hypothesis_repository.create(hypothesis)
        await self.hypothesis_repository.commit()
        hypothesis = await self.hypothesis_repository.get_by_id(hypothesis.id)
        return self.hypothesis_mapper.hypothesis_schema_to_dto(hypothesis)

    async def update_hypothesis(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE, data: HypothesisUpdateDTO
    ) -> HypothesisDTO:
        try:
            hypothesis = await self.hypothesis_repository.get_by_id(hypothesis_id)
            if not hypothesis:
                raise HypothesisNotFoundError(f"Hypothesis {hypothesis_id} not found")
        except DBNotFoundError:
            raise HypothesisNotFoundError(f"Hypothesis {hypothesis_id} not found")
        if not await self.permission_checker.can_edit_hypothesis(
            user.id, hypothesis.project_id
        ):
            raise HypothesisNotAccessibleError(
                f"Hypothesis {hypothesis_id} not accessible"
            )
        updates = self.hypothesis_mapper.hypothesis_update_dto_to_update_dict(data)
        result = await self.hypothesis_repository.update(hypothesis_id, **updates)
        await self.hypothesis_repository.commit()
        return self.hypothesis_mapper.hypothesis_schema_to_dto(result)

    async def delete_hypothesis(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE
    ) -> bool:
        hypothesis = await self.hypothesis_repository.get_by_id(hypothesis_id)
        if not hypothesis:
            raise HypothesisNotFoundError(f"Hypothesis {hypothesis_id} not found")
        if not await self.permission_checker.can_delete_hypothesis(
            user.id, hypothesis.project_id
        ):
            raise HypothesisNotAccessibleError(
                f"Hypothesis {hypothesis_id} not accessible"
            )
        await self.hypothesis_repository.delete(hypothesis_id)
        await self.hypothesis_repository.commit()
        return True
