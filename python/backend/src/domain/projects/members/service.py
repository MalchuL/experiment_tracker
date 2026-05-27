from __future__ import annotations

from typing import Dict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.errors import ProjectNotAccessibleError
from domain.projects.repository import ProjectRepository
from domain.rbac.permissions import ProjectActions
from domain.rbac.permissions.project import PROJECT_ACTIONS, infer_role_from_allowed_map
from domain.rbac.repository import PermissionRepository
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import PermissionChecker
from domain.projects.members.dto import (
    ProjectMemberInviteDTO,
    ProjectMemberRemoveDTO,
    ProjectMemberRowDTO,
    ProjectMemberUpdateRoleDTO,
    UserLookupDTO,
)
from domain.projects.members.errors import (
    ProjectMemberAccessDenied,
    ProjectMemberInvalidRole,
    ProjectMemberLastEditor,
    ProjectMemberNotFound,
)
from models import Permission, Project, Role, User


class ProjectMembersService:
    """Application service for project member management.

    The service combines direct project permission rows with inherited team access,
    exposes effective member rows for the UI, and writes project-scoped role
    overrides through ``PermissionService``.
    """

    def __init__(
        self,
        db: AsyncSession,
        project_repository: ProjectRepository,
        permission_repository: PermissionRepository,
        permission_service: PermissionService,
        permission_checker: PermissionChecker,
    ):
        self.db = db
        self.project_repository = project_repository
        self.permission_repository = permission_repository
        self.permission_service = permission_service
        self.permission_checker = permission_checker

    async def _ensure_project_view(self, requester_id: UUID, project_id: UUID):
        if not await self.permission_checker.can_view_project(requester_id, project_id):
            raise ProjectMemberAccessDenied("Cannot view project members")

    async def _ensure_project_edit(self, requester_id: UUID, project_id: UUID):
        if not await self.permission_checker.can_edit_project(requester_id, project_id):
            raise ProjectMemberAccessDenied("Cannot manage project members")

    @staticmethod
    def _user_belongs_to_project_team(project: Project, user_id: UUID) -> bool:
        if not project.team_id or project.team is None:
            return False
        if project.team.owner_id == user_id:
            return True
        return any(
            m.user_id == user_id for m in (project.team.member_links or [])
        )

    @staticmethod
    def _allowed_map_from_permissions(perms: list[Permission]) -> dict[str, bool]:
        base = {action: False for action in PROJECT_ACTIONS}
        for p in perms:
            if p.action in base:
                base[p.action] = base[p.action] or p.allowed
        return base

    async def _load_users(self, user_ids: set[UUID]) -> Dict[UUID, User]:
        if not user_ids:
            return {}
        stmt = select(User).where(User.id.in_(list(user_ids)))
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return {u.id: u for u in rows}

    async def list_members(
        self, requester_id: UUID, project_id: UUID
    ) -> list[ProjectMemberRowDTO]:
        """List effective project members and their editable state.

        Args:
            requester_id: User requesting the member list.
            project_id: Project whose membership should be listed.

        Returns:
            list[ProjectMemberRowDTO]: Direct users, team-inherited users, and
            override rows with effective roles and UI permissions.

        Raises:
            ProjectMemberAccessDenied: If the requester cannot view the project.
            ProjectNotAccessibleError: If the project cannot be loaded.
        """
        await self._ensure_project_view(requester_id, project_id)
        project = await self.project_repository.get_project_for_member_list(project_id)
        if project is None:
            raise ProjectNotAccessibleError("Project not found")

        direct_user_ids = set(
            await self.permission_repository.list_distinct_user_ids_for_project(
                project_id
            )
        )
        team_user_ids: set[UUID] = set()
        if project.team_id and project.team is not None:
            team_user_ids.add(project.team.owner_id)
            for link in project.team.member_links or []:
                team_user_ids.add(link.user_id)

        all_ids = direct_user_ids | team_user_ids
        users_by_id = await self._load_users(all_ids)

        can_manage = await self.permission_checker.can_edit_project(
            requester_id, project_id
        )

        rows: list[ProjectMemberRowDTO] = []
        for uid in sorted(all_ids, key=lambda x: str(x)):
            user = users_by_id.get(uid)
            email = user.email if user else None
            display_name = user.display_name if user else None

            direct_rows = await self.permission_repository.get_permissions(
                user_id=uid, project_id=project_id
            )
            has_direct = len(direct_rows) > 0
            in_team = self._user_belongs_to_project_team(project, uid)
            if uid == project.owner_id:
                access_source = "direct"
            elif has_direct and in_team:
                access_source = "override"
            elif has_direct:
                access_source = "direct"
            else:
                access_source = "team"

            if has_direct:
                role = infer_role_from_allowed_map(
                    self._allowed_map_from_permissions(direct_rows)
                )
                if role == Role.OWNER and uid != project.owner_id:
                    role = Role.ADMIN
                if role == Role.ADMIN and uid == project.owner_id:
                    role = Role.OWNER
            elif project.team_id and project.team is not None:
                if uid == project.team.owner_id:
                    role = Role.OWNER
                else:
                    tm = next(
                        (
                            m
                            for m in (project.team.member_links or [])
                            if m.user_id == uid
                        ),
                        None,
                    )
                    role = tm.role if tm is not None else Role.VIEWER
            else:
                role = Role.VIEWER

            can_edit = can_manage and uid != project.owner_id
            can_remove = can_manage and uid != project.owner_id and has_direct
            rows.append(
                ProjectMemberRowDTO(
                    user_id=uid,
                    email=email,
                    display_name=display_name,
                    role=role,
                    access_source=access_source,  # type: ignore[arg-type]
                    can_edit=can_edit,
                    can_remove=can_remove,
                )
            )
        return rows

    async def lookup_user_by_email(
        self, requester_id: UUID, project_id: UUID, email: str
    ) -> UserLookupDTO:
        """Find an active user by email for project invites.

        Args:
            requester_id: User performing the lookup.
            project_id: Project where the user would be invited.
            email: Email address to normalize and search.

        Returns:
            UserLookupDTO: Basic user identity for invite confirmation.

        Raises:
            ProjectMemberAccessDenied: If the requester cannot manage the project.
            ProjectNotAccessibleError: If the project does not exist.
            ProjectMemberNotFound: If no active user has the email address.
        """
        await self._ensure_project_edit(requester_id, project_id)
        project = await self.project_repository.get_project_by_id(project_id)
        if project is None:
            raise ProjectNotAccessibleError("Project not found")
        normalized = email.strip().lower()
        stmt = select(User).where(
            func.lower(User.email) == normalized,
            User.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ProjectMemberNotFound("User not found")
        return UserLookupDTO(
            id=user.id, email=user.email, display_name=user.display_name
        )

    def _reject_owner_role(self, role: Role) -> None:
        if role == Role.OWNER:
            raise ProjectMemberInvalidRole("Cannot assign owner role via members API")

    async def invite_member(
        self, requester_id: UUID, project_id: UUID, data: ProjectMemberInviteDTO
    ) -> ProjectMemberRowDTO:
        """Invite an existing active user to a project by email.

        Args:
            requester_id: User granting access.
            project_id: Project receiving the new direct permission rows.
            data: Invite payload containing email and role.

        Returns:
            ProjectMemberRowDTO: Effective member row after permissions are written.

        Raises:
            ProjectMemberAccessDenied: If the requester cannot manage the project.
            ProjectMemberInvalidRole: If the payload attempts to assign owner access
                or changes the project owner.
            ProjectNotAccessibleError: If the project cannot be loaded.
            ProjectMemberNotFound: If the target user does not exist or cannot be
                found after the invite is written.
        """
        await self._ensure_project_edit(requester_id, project_id)
        self._reject_owner_role(data.role)
        project = await self.project_repository.get_project_by_id(project_id)
        if project is None:
            raise ProjectNotAccessibleError("Project not found")
        normalized = data.email.strip().lower()
        stmt = select(User).where(
            func.lower(User.email) == normalized,
            User.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ProjectMemberNotFound("User not found")
        if user.id == project.owner_id:
            raise ProjectMemberInvalidRole("Owner already has full access")

        await self.permission_service.add_user_to_project_permissions(
            user.id, project_id, data.role
        )
        await self.db.commit()

        rows = await self.list_members(requester_id, project_id)
        match = next((r for r in rows if r.user_id == user.id), None)
        if match is None:
            raise ProjectMemberNotFound("Member not listed after invite")
        return match

    async def update_member_role(
        self, requester_id: UUID, project_id: UUID, data: ProjectMemberUpdateRoleDTO
    ) -> ProjectMemberRowDTO:
        """Update a direct project role or create a team-member override.

        Args:
            requester_id: User changing the role.
            project_id: Project whose member role should change.
            data: Target user id and replacement role.

        Returns:
            ProjectMemberRowDTO: Effective member row after the permission update.

        Raises:
            ProjectMemberAccessDenied: If the requester cannot manage the project, the
                target is the owner, or the target has neither team nor direct access.
            ProjectMemberInvalidRole: If owner role is requested.
            ProjectNotAccessibleError: If the project cannot be loaded.
            ProjectMemberNotFound: If the target cannot be found after the update.
        """
        await self._ensure_project_edit(requester_id, project_id)
        self._reject_owner_role(data.role)
        project = await self.project_repository.get_project_for_member_list(project_id)
        if project is None:
            raise ProjectNotAccessibleError("Project not found")
        if data.user_id == project.owner_id:
            raise ProjectMemberAccessDenied("Cannot change the project owner's role")

        direct_rows = await self.permission_repository.get_permissions(
            user_id=data.user_id, project_id=project_id
        )
        in_team = self._user_belongs_to_project_team(project, data.user_id)
        if not direct_rows and not in_team:
            raise ProjectMemberAccessDenied(
                "User is not on this project's team; grant access via invite first"
            )

        if direct_rows:
            await self.permission_service.update_user_project_role_permissions(
                data.user_id, project_id, data.role
            )
        else:
            await self.permission_service.add_user_to_project_permissions(
                data.user_id, project_id, data.role
            )
        await self.db.commit()

        rows = await self.list_members(requester_id, project_id)
        match = next((r for r in rows if r.user_id == data.user_id), None)
        if match is None:
            raise ProjectMemberNotFound("Member not found")
        return match

    async def remove_member(
        self, requester_id: UUID, project_id: UUID, data: ProjectMemberRemoveDTO
    ) -> None:
        """Remove a user's direct project permission rows.

        Team-inherited access is not removed here; deleting direct rows causes team
        members to fall back to their team role. Standalone projects keep at least one
        editor.

        Args:
            requester_id: User removing access.
            project_id: Project whose direct permissions should be removed.
            data: Target user id.

        Returns:
            None: Permission rows are removed and committed.

        Raises:
            ProjectMemberAccessDenied: If the requester cannot manage the project, the
                target is the owner, there are no direct rows to remove, or removal
                would leave a standalone project without an editor.
            ProjectMemberLastEditor: If removing the target would remove the last
                editor from a non-team project.
            ProjectNotAccessibleError: If the project cannot be loaded.
        """
        await self._ensure_project_edit(requester_id, project_id)
        project = await self.project_repository.get_project_for_member_list(project_id)
        if project is None:
            raise ProjectNotAccessibleError("Project not found")
        if data.user_id == project.owner_id:
            raise ProjectMemberAccessDenied("Cannot remove the project owner")

        direct_rows = await self.permission_repository.get_permissions(
            user_id=data.user_id, project_id=project_id
        )
        if not direct_rows:
            raise ProjectMemberAccessDenied(
                "Nothing to remove: this user only has team access with no project override"
            )

        if project.team_id is None:
            allowed_map = self._allowed_map_from_permissions(direct_rows)
            if allowed_map.get(ProjectActions.EDIT_PROJECT):
                others_with_edit = 0
                for uid in await self.permission_repository.list_distinct_user_ids_for_project(
                    project_id
                ):
                    if uid == data.user_id:
                        continue
                    other_rows = await self.permission_repository.get_permissions(
                        user_id=uid, project_id=project_id
                    )
                    om = self._allowed_map_from_permissions(other_rows)
                    if om.get(ProjectActions.EDIT_PROJECT):
                        others_with_edit += 1
                if others_with_edit == 0:
                    raise ProjectMemberLastEditor(
                        "Cannot remove the last user with edit access on this project"
                    )

        await self.permission_service.remove_user_from_project_permissions(
            data.user_id, project_id
        )
        await self.db.commit()
