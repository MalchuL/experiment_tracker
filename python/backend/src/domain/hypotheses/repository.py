from typing import List
from advanced_alchemy.filters import LimitOffset
from lib.db.base_repository import BaseRepository, ListOptions
from lib.types import UUID_TYPE
from models import Hypothesis, Project
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from lib.protocols.user_protocol import UserProtocol


class HypothesisRepository(BaseRepository[Hypothesis]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Hypothesis)

    async def get_hypotheses_by_project(
        self, project_id: UUID_TYPE | list[UUID_TYPE]
    ) -> List[Hypothesis]:
        conditions = []
        if isinstance(project_id, (list, tuple)):
            conditions.append(Hypothesis.project_id.in_(project_id))
        else:
            conditions.append(Hypothesis.project_id == project_id)
        hypotheses = await self.advanced_alchemy_repository.list(
            *conditions,
            order_by=Hypothesis.created_at.desc(),
        )
        return hypotheses
