from typing import List

from domain.projects.access import ProjectAccessService
from domain.projects.errors import ProjectNotAccessibleError
from domain.projects.service import ProjectService
from domain.rbac.permissions import PROJECT_EDIT, PROJECT_VIEW
from lib.db.base_repository import ListOptions
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession

from .dto import HypothesisCreateDTO, HypothesisDTO, HypothesisUpdateDTO
from .error import HypothesisNotAccessibleError
from .mapper import HypothesisMapper
from .repository import HypothesisRepository


class HypothesisService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.hypothesis_repository = HypothesisRepository(db)
        self.project_service = ProjectService(db)
        self.access_service = ProjectAccessService(db)
        self.hypothesis_mapper = HypothesisMapper()

    async def get_accessible_hypotheses(
        self, user: UserProtocol
    ) -> List[HypothesisDTO]:
        hypotheses = await self.hypothesis_repository.get_accessible_hypotheses(user)
        return self.hypothesis_mapper.hypothesis_list_schema_to_dto(hypotheses)

    async def get_recent_hypotheses(
        self, user: UserProtocol, limit: int = 10
    ) -> List[HypothesisDTO]:
        hypotheses = await self.hypothesis_repository.get_accessible_hypotheses(
            user, ListOptions(limit=limit, offset=0)
        )
        return self.hypothesis_mapper.hypothesis_list_schema_to_dto(hypotheses)

    async def get_hypotheses_by_project(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> List[HypothesisDTO]:
        await self.access_service.require_project_permission(
            user, project_id, PROJECT_VIEW
        )
        hypotheses = await self.hypothesis_repository.get_hypotheses_by_project(
            user, project_id
        )
        return self.hypothesis_mapper.hypothesis_list_schema_to_dto(hypotheses)

    async def get_hypothesis_if_accessible(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE
    ) -> HypothesisDTO | None:
        hypothesis = await self.hypothesis_repository.get_hypothesis_if_accessible(
            user, hypothesis_id
        )
        if not hypothesis:
            return None
        return self.hypothesis_mapper.hypothesis_schema_to_dto(hypothesis)

    async def create_hypothesis(
        self, user: UserProtocol, data: HypothesisCreateDTO
    ) -> HypothesisDTO:
        await self.access_service.require_project_permission(
            user, data.project_id, PROJECT_EDIT
        )
        project = await self.project_service.get_project_if_accessible(
            user, data.project_id
        )
        if not project:
            raise ProjectNotAccessibleError(f"Project {data.project_id} not accessible")
        hypothesis = self.hypothesis_mapper.hypothesis_create_dto_to_schema(data)
        await self.hypothesis_repository.create(hypothesis)
        await self.hypothesis_repository.commit()
        hypothesis = await self.hypothesis_repository.get_hypothesis_if_accessible(
            user, hypothesis.id
        )
        if not hypothesis:
            raise HypothesisNotAccessibleError(
                f"Hypothesis {hypothesis.id} not accessible"
            )
        return self.hypothesis_mapper.hypothesis_schema_to_dto(hypothesis)

    async def update_hypothesis(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE, data: HypothesisUpdateDTO
    ) -> HypothesisDTO:
        hypothesis = await self.hypothesis_repository.get_hypothesis_if_accessible(
            user, hypothesis_id
        )
        if not hypothesis:
            raise HypothesisNotAccessibleError(
                f"Hypothesis {hypothesis_id} not accessible"
            )
        await self.access_service.require_project_permission(
            user, hypothesis.project_id, PROJECT_EDIT
        )
        updates = self.hypothesis_mapper.hypothesis_update_dto_to_update_dict(data)
        result = await self.hypothesis_repository.update(hypothesis_id, **updates)
        await self.hypothesis_repository.commit()
        return self.hypothesis_mapper.hypothesis_schema_to_dto(result)

    async def delete_hypothesis(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE
    ) -> bool:
        hypothesis = await self.hypothesis_repository.get_hypothesis_if_accessible(
            user, hypothesis_id
        )
        if not hypothesis:
            raise HypothesisNotAccessibleError(
                f"Hypothesis {hypothesis_id} not accessible"
            )
        await self.access_service.require_project_permission(
            user, hypothesis.project_id, PROJECT_EDIT
        )
        await self.hypothesis_repository.delete(hypothesis_id)
        await self.hypothesis_repository.commit()
        return True
