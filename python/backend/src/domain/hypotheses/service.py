from typing import List

from domain.projects.errors import ProjectNotAccessibleError
from domain.projects.service import ProjectService
from domain.rbac.permissions import ProjectActions
from domain.rbac.wrapper import PermissionChecker
from domain.utils.project_based_service import ProjectBasedService
from lib.db.base_repository import DBNotFoundError
from lib.pagination import ListOptions
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession

from .dto import (
    HypothesisCreateDTO,
    HypothesisDTO,
    HypothesisListResponseDTO,
    HypothesisUpdateDTO,
)
from .error import HypothesisNotAccessibleError, HypothesisNotFoundError
from .mapper import HypothesisMapper
from .repository import HypothesisRepository


class HypothesisService:
    """Application service for project hypotheses.

    The service coordinates hypothesis persistence, DTO mapping, project-level RBAC,
    and transaction commits for create, update, and delete operations.
    """

    def __init__(
        self,
        db: AsyncSession,
        hypothesis_repository: HypothesisRepository,
        permission_checker: PermissionChecker,
    ):
        self.db = db
        self.hypothesis_repository = hypothesis_repository
        self.permission_checker = permission_checker
        self.hypothesis_mapper = HypothesisMapper()

    async def get_hypotheses_by_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(),
    ) -> HypothesisListResponseDTO:
        """List hypotheses attached to a project.

        Args:
            user: User requesting the list.
            project_id: Project whose hypotheses should be returned.
            list_options: Pagination limit and offset.

        Returns:
            HypothesisListResponseDTO: Paginated hypothesis DTOs.

        Raises:
            ProjectNotAccessibleError: If the user cannot view hypotheses in the
                project.
        """
        if not await self.permission_checker.can_view_hypothesis(user.id, project_id):
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        hypotheses_page = await self.hypothesis_repository.get_hypotheses_by_project(
            project_id,
            list_options=list_options,
        )
        return HypothesisListResponseDTO.from_page(
            hypotheses_page.map(
                self.hypothesis_mapper.hypothesis_schema_to_dto
            )
        )

    async def get_hypothesis_if_accessible(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE
    ) -> HypothesisDTO:
        """Load one hypothesis if the user can view its project.

        Args:
            user: User requesting the hypothesis.
            hypothesis_id: Hypothesis identifier.

        Returns:
            HypothesisDTO: Full hypothesis DTO.

        Raises:
            HypothesisNotFoundError: If the hypothesis row does not exist.
            HypothesisNotAccessibleError: If the user lacks view permission.
        """
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
        """Create a hypothesis in a project.

        Args:
            user: User creating the hypothesis.
            data: Create payload containing the project id and hypothesis fields.

        Returns:
            HypothesisDTO: Newly persisted hypothesis after commit and reload.

        Raises:
            HypothesisNotAccessibleError: If the user cannot create hypotheses in the
                target project.
        """
        if not await self.permission_checker.can_create_hypothesis(
            user.id, data.project_id
        ):
            raise HypothesisNotAccessibleError(
                f"Project {data.project_id} not accessible"
            )
        hypothesis = self.hypothesis_mapper.hypothesis_create_dto_to_schema(data)
        await self.hypothesis_repository.create(hypothesis)
        await self.db.commit()
        hypothesis = await self.hypothesis_repository.get_by_id(hypothesis.id)
        return self.hypothesis_mapper.hypothesis_schema_to_dto(hypothesis)

    async def update_hypothesis(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE, data: HypothesisUpdateDTO
    ) -> HypothesisDTO:
        """Update an existing hypothesis.

        Args:
            user: User editing the hypothesis.
            hypothesis_id: Hypothesis identifier.
            data: Update payload; only mapped fields are persisted.

        Returns:
            HypothesisDTO: Updated hypothesis DTO.

        Raises:
            HypothesisNotFoundError: If the hypothesis does not exist.
            HypothesisNotAccessibleError: If the user cannot edit the hypothesis's
                project.
        """
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
        await self.db.commit()
        return self.hypothesis_mapper.hypothesis_schema_to_dto(result)

    async def delete_hypothesis(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE
    ) -> bool:
        """Delete a hypothesis row.

        Args:
            user: User deleting the hypothesis.
            hypothesis_id: Hypothesis identifier.

        Returns:
            bool: Always ``True`` after the repository delete and commit succeed.

        Raises:
            HypothesisNotFoundError: If the hypothesis does not exist.
            HypothesisNotAccessibleError: If the user lacks delete permission.
        """
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
        await self.db.commit()
        return True
