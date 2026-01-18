# repositories/permission_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from lib.db.base_repository import BaseRepository
from models import Permission

from .error import InvalidIdError, InvalidScopeError


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db: AsyncSession, auto_commit: bool = True):
        self.auto_commit = auto_commit
        super().__init__(db, Permission)

    def _validate_scope(
        self,
        team_id: Optional[UUID],
        project_id: Optional[UUID],
    ) -> None:
        if not team_id and not project_id:
            raise InvalidScopeError("Either team_id or project_id must be provided.")
        if team_id and project_id:
            raise InvalidScopeError(
                "Only one of team_id or project_id can be provided."
            )

    @staticmethod
    def _scope_filters(
        *,
        team_id: UUID | None,
        project_id: UUID | None,
    ) -> list:
        return [
            Permission.team_id == team_id,
            Permission.project_id == project_id,
        ]

    async def get_permissions(
        self,
        *,
        permission_id: UUID | None = None,
        user_id: UUID | None = None,
        team_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        actions: list[str] | str | None = None,
    ) -> list[Permission]:
        """
        Get all permissions for a user by scope.
        1. If team_id and project_id are not provided, return all permissions for the user.
        2. If team_id or project_id is not None, return all permissions for the user in a given scope (team_id or project_id).
        3. If actions are provided, return all permissions for the user with the given actions.
        """
        conditions = []
        if permission_id is not None:
            if (user_id, team_id, project_id, actions) != (None, None, None, None):
                raise InvalidScopeError(
                    "Only one of permission_id, user_id, team_id, project_id can be provided."
                )
            conditions.append(Permission.id == permission_id)
        else:
            if user_id is None and team_id is None and project_id is None:
                raise InvalidScopeError(
                    "At least one of user_id, team_id, project_id must be provided."
                )

            if user_id is not None:
                conditions.append(Permission.user_id == user_id)

            if actions is not None:
                if isinstance(actions, str):
                    conditions.append(Permission.action == actions)
                else:
                    conditions.append(Permission.action.in_(actions))

            if team_id is not None or project_id is not None:
                conditions.extend(
                    self._scope_filters(team_id=team_id, project_id=project_id)
                )
        return await self.advanced_alchemy_repository.list(*conditions)

    async def create_permission(self, permission: Permission) -> Permission:
        self._validate_scope(
            team_id=permission.team_id, project_id=permission.project_id
        )
        return await self.advanced_alchemy_repository.add(
            permission, auto_refresh=True, auto_commit=self.auto_commit
        )

    async def update_permission(self, permission: Permission) -> Permission:
        self._validate_scope(
            team_id=permission.team_id, project_id=permission.project_id
        )
        return await self.advanced_alchemy_repository.update(
            permission, auto_commit=self.auto_commit
        )

    async def delete_permission(
        self,
        id: UUID | str | list[UUID | str] | Permission | list[Permission],
    ) -> None:
        if isinstance(id, (UUID, str)):
            await self.advanced_alchemy_repository.delete(
                id, auto_commit=self.auto_commit
            )
        elif isinstance(id, list):
            for item in id:
                if isinstance(item, (UUID, str)):
                    await self.advanced_alchemy_repository.delete(
                        item, auto_commit=False
                    )
                elif isinstance(item, Permission):
                    await self.advanced_alchemy_repository.delete(
                        item.id, auto_commit=False
                    )
                else:
                    raise InvalidIdError("Invalid id type")
            if self.auto_commit:
                await self.db.commit()
        elif isinstance(id, Permission):
            await self.advanced_alchemy_repository.delete(
                id.id, auto_commit=self.auto_commit
            )
        else:
            raise InvalidIdError("Invalid id type")
