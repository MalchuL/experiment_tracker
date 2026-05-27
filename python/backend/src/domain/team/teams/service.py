from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from domain.team.teams.repository import TeamRepository
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import PermissionChecker
from uuid import UUID
from domain.team.teams.errors import (
    TeamMemberAlreadyExistsError,
    TeamAccessDeniedError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
)
from lib.db.error import DBNotFoundError
from .dto import (
    TeamCreateDTO,
    TeamDeleteResponseDTO,
    TeamListItemDTO,
    TeamMemberDeleteDTO,
    TeamMemberReadDTO,
    TeamMemberUpdateDTO,
    TeamMemberWithUserDTO,
    TeamMemberCreateDTO,
    TeamReadDTO,
    TeamUpdateDTO,
    TeamUserLookupDTO,
)
from .mapper import TeamMapper, CreateDTOToSchemaProps
from lib.pagination import ListOptions, Page, paginate_sequence
from models import Role, User
from clients.object_storage import ObjectStorageClientProtocol
from domain.projects.repository import ProjectRepository
from domain.scalars.service import NoOpScalarsService, ScalarsServiceProtocol
from lib.category_cleanup_dto import CategoryCleanupErrorEntryDTO, CategoryCleanupResultEntryDTO
from lib.deletion_outcome import (
    append_postgres_deleted,
    finalize_deletion_outcome,
    outcome_lists_from_project_teardown,
)
from domain.projects.satellite_teardown import teardown_project_for_delete


class TeamService:
    """Teams and membership: create/update teams, manage members, delete team and owned projects.

    Team deletion walks projects under the team and runs the same satellite cleanup as
    project deletion (object storage + scalars) before removing rows.
    """

    def __init__(
        self,
        db: AsyncSession,
        team_repository: TeamRepository,
        permission_checker: PermissionChecker,
        permission_service: PermissionService,
        project_repository: ProjectRepository | None = None,
        scalars_service: ScalarsServiceProtocol | None = None,
        object_storage_client: ObjectStorageClientProtocol | None = None,
    ):
        """Initialize the team service.

        Args:
            db: Database session used for team and permission commits.
            team_repository: Repository for team and membership rows.
            permission_checker: RBAC checker for team actions.
            permission_service: Service that writes team/project permission rows.
            project_repository: Optional repository used for team deletion cleanup.
            scalars_service: Optional scalars facade used to clean team-owned projects.
            object_storage_client: Optional object-storage client used for project
                artifact cleanup during team deletion.
        """
        self.db = db
        self.team_repository = team_repository
        self.permission_service = permission_service
        self.permission_checker = permission_checker
        self.project_repository = project_repository
        self.scalars_service = scalars_service or NoOpScalarsService()
        self.object_storage_client = object_storage_client
        self.team_mapper = TeamMapper()

    async def _get_user_role(self, user_id: UUID, team_id: UUID) -> Role | None:
        try:
            team = await self.team_repository.get_by_id(team_id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")
        if str(team.owner_id) == str(user_id):
            return Role.OWNER
        member = await self.team_repository.get_team_member_if_accessible(
            user_id, team_id
        )
        if member is None:
            return None
        return member.role

    async def _check_role(
        self,
        editor_user_id: UUID,
        team_id: UUID,
        new_role: Role,
        target_user_id: UUID | None = None,
    ) -> None:
        editor_role = await self._get_user_role(editor_user_id, team_id)
        if editor_role is None:
            raise TeamAccessDeniedError("You do not have permission to edit roles")

        role_rank = {
            Role.VIEWER: 0,
            Role.MEMBER: 1,
            Role.ADMIN: 2,
            Role.OWNER: 3,
        }
        if role_rank[new_role] >= role_rank[editor_role]:
            raise TeamAccessDeniedError(
                "You do not have permission to assign this role"
            )

        if target_user_id is not None:
            target_member = await self.team_repository.get_team_member_if_accessible(
                target_user_id, team_id
            )
            if (
                target_member is not None
                and target_member.role == Role.ADMIN
                and new_role != Role.ADMIN
            ):
                raise TeamAccessDeniedError(
                    "You do not have permission to change an admin role"
                )

    # Team
    async def create_team(self, user_id: UUID, dto: TeamCreateDTO) -> TeamReadDTO:
        """Create a team and grant the creator admin permissions.

        Args:
            user_id: User who owns/creates the team.
            dto: Team create payload.

        Returns:
            TeamReadDTO: Created team metadata.
        """
        team = self.team_mapper.team_dto_to_schema(
            dto, CreateDTOToSchemaProps(owner_id=user_id)
        )
        await self.team_repository.create(team)
        await self.permission_service.add_user_to_team_permissions(
            user_id, team.id, Role.ADMIN
        )
        await self.db.commit()

        return self.team_mapper.team_schema_to_dto(team)

    async def update_team(self, user_id: UUID, dto: TeamUpdateDTO) -> TeamReadDTO:
        """Update team metadata.

        Args:
            user_id: User performing the update.
            dto: Update payload including the team id.

        Returns:
            TeamReadDTO: Updated team metadata.

        Raises:
            TeamAccessDeniedError: If the user cannot manage the team.
            TeamNotFoundError: If the team does not exist.
        """
        if not await self.permission_checker.can_manage_team(user_id, dto.id):
            raise TeamAccessDeniedError("You do not have permission to update a team")
        try:
            await self.team_repository.get_by_id(dto.id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")
        update_data = self.team_mapper.team_update_dto_to_dict(dto)
        update_data.pop("id", None)
        team = await self.team_repository.update(dto.id, **update_data)
        await self.db.commit()
        return self.team_mapper.team_schema_to_dto(team)

    async def delete_team(
        self, user_id: UUID, team_id: UUID, *, detailed: bool = False
    ) -> TeamDeleteResponseDTO:
        """Delete the team after removing every team-owned project and satellite data.

        For each project: same sequence as ``ProjectService.delete_project`` — per
        experiment object-storage + scalars deletes, project-level object storage delete,
        scalars ``delete_project_table``, expunge ORM graphs, then delete the project row.
        Finally deletes the team row. Requires team manage permission.

        Args:
            user_id: User deleting the team.
            team_id: Team identifier.
            detailed: Whether to include full per-step cleanup results.

        Returns:
            TeamDeleteResponseDTO: Structured cleanup outcome.

        Raises:
            TeamAccessDeniedError: If the user cannot manage the team.
            TeamNotFoundError: If the team does not exist.
        """
        if not await self.permission_checker.can_manage_team(user_id, team_id):
            raise TeamAccessDeniedError("You do not have permission to delete a team")
        try:
            await self.team_repository.get_by_id(team_id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")
        results: list[CategoryCleanupResultEntryDTO] = []
        errors: list[CategoryCleanupErrorEntryDTO] = []
        if self.project_repository is not None:
            projects = await self.project_repository.get_projects_by_team(team_id)
            for project in projects:
                experiment_ids = [e.id for e in list(project.experiments or [])]
                teardown = await teardown_project_for_delete(
                    project.id,
                    experiment_ids,
                    self.object_storage_client,
                    self.scalars_service,
                )
                r, e = outcome_lists_from_project_teardown(teardown)
                results.extend(r)
                errors.extend(e)
                for experiment in list(project.experiments or []):
                    self.project_repository.expunge(experiment)
                self.project_repository.expunge(project)
                await self.project_repository.delete(project.id)
                append_postgres_deleted(
                    results, category="postgres:project", entity_id=project.id
                )
        await self.team_repository.delete(team_id)
        await self.db.commit()
        append_postgres_deleted(results, category="postgres:team", entity_id=team_id)
        finalized = finalize_deletion_outcome(results, errors, detailed=detailed)
        return TeamDeleteResponseDTO.model_validate(finalized.model_dump())

    async def list_teams(
        self, user_id: UUID, list_options: ListOptions
    ) -> Page[TeamListItemDTO]:
        """List teams accessible to a user.

        Args:
            user_id: User whose teams should be listed.
            list_options: Pagination limit and offset.

        Returns:
            Page[TeamListItemDTO]: Paginated team rows including whether the user can
            create projects in each team.
        """
        teams = await self.team_repository.list_teams_for_user(user_id)
        items: list[TeamListItemDTO] = []
        for team in teams:
            base = self.team_mapper.team_schema_to_dto(team)
            can_create = await self.permission_checker.can_create_project(
                user_id, team.id
            )
            items.append(
                TeamListItemDTO.model_validate(
                    {**base.model_dump(), "can_create_project": can_create}
                )
            )
        page = paginate_sequence(items, list_options)
        return page

    async def get_team(self, user_id: UUID, team_id: UUID) -> TeamReadDTO:
        """Load a team if the user can view it.

        Args:
            user_id: User requesting the team.
            team_id: Team identifier.

        Returns:
            TeamReadDTO: Team metadata.

        Raises:
            TeamAccessDeniedError: If the user cannot view the team.
            TeamNotFoundError: If the team does not exist.
        """
        if not await self.permission_checker.can_view_team(user_id, team_id):
            raise TeamAccessDeniedError("You do not have permission to view this team")
        try:
            team = await self.team_repository.get_by_id(team_id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")
        return self.team_mapper.team_schema_to_dto(team)

    async def list_team_members(
        self, user_id: UUID, team_id: UUID
    ) -> list[TeamMemberWithUserDTO]:
        """List team members with user metadata and a synthetic owner row.

        Args:
            user_id: User requesting members.
            team_id: Team identifier.

        Returns:
            list[TeamMemberWithUserDTO]: Owner and non-owner members.

        Raises:
            TeamAccessDeniedError: If the user cannot view the team.
            TeamNotFoundError: If the team does not exist.
        """
        if not await self.permission_checker.can_view_team(user_id, team_id):
            raise TeamAccessDeniedError("You do not have permission to view this team")
        try:
            team = await self.team_repository.get_by_id_with_owner(team_id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")
        members = await self.team_repository.list_team_members_with_users(team_id)
        owner = team.owner
        out: list[TeamMemberWithUserDTO] = []
        if team.owner_id is not None and owner is not None:
            out.append(
                TeamMemberWithUserDTO(
                    member_id=None,
                    user_id=team.owner_id,
                    team_id=team_id,
                    role=Role.OWNER,
                    email=owner.email,
                    display_name=owner.display_name,
                    is_team_owner=True,
                )
            )
        owner_in_members = False
        for tm in members:
            if tm.user_id == team.owner_id:
                owner_in_members = True
                continue
            u = tm.user
            out.append(
                TeamMemberWithUserDTO(
                    member_id=tm.id,
                    user_id=tm.user_id,
                    team_id=tm.team_id,
                    role=tm.role,
                    email=u.email,
                    display_name=u.display_name,
                    is_team_owner=False,
                )
            )
        if owner_in_members:
            # Owner also has a team_members row; synthetic owner row already covers them.
            pass
        return out

    async def lookup_user_by_email(
        self, requester_id: UUID, team_id: UUID, email: str
    ) -> TeamUserLookupDTO:
        """Look up an active user by email for team membership changes.

        Args:
            requester_id: User performing the lookup.
            team_id: Team where membership would be changed.
            email: Email address to normalize and search.

        Returns:
            TeamUserLookupDTO: Matching active user's identity.

        Raises:
            TeamAccessDeniedError: If the requester cannot manage the team.
            TeamNotFoundError: If the team does not exist.
            TeamMemberNotFoundError: If no active user matches the email.
        """
        if not await self.permission_checker.can_manage_team(requester_id, team_id):
            raise TeamAccessDeniedError("You do not have permission to look up users")
        try:
            await self.team_repository.get_by_id(team_id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")
        normalized = email.strip().lower()
        stmt = select(User).where(
            func.lower(User.email) == normalized,
            User.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise TeamMemberNotFoundError("User not found")
        return TeamUserLookupDTO(
            id=user.id, email=user.email, display_name=user.display_name
        )

    # Team Member
    async def add_team_member(
        self, user_id: UUID, team_member: TeamMemberCreateDTO
    ) -> TeamMemberReadDTO:
        """Add a user to a team and grant role permissions.

        Args:
            user_id: Manager performing the add.
            team_member: Target user, team id, and role.

        Returns:
            TeamMemberReadDTO: Created membership row.

        Raises:
            TeamAccessDeniedError: If the manager cannot assign the requested role or
                manage the team.
            TeamMemberAlreadyExistsError: If the target is already a member.
            TeamNotFoundError: If role checking cannot load the team.
        """
        await self._check_role(user_id, team_member.team_id, team_member.role)
        if not await self.permission_checker.can_manage_team(
            user_id, team_member.team_id
        ):
            raise TeamAccessDeniedError(
                "You do not have permission to add a team member"
            )
        if await self.team_repository.get_team_member_if_accessible(
            team_member.user_id, team_member.team_id
        ):
            raise TeamMemberAlreadyExistsError("Team member already exists")

        team_member = self.team_mapper.team_member_dto_to_schema(team_member)
        await self.team_repository.add_team_member(team_member)
        await self.permission_service.add_user_to_team_permissions(
            team_member.user_id, team_member.team_id, team_member.role
        )
        await self.db.commit()
        return self.team_mapper.team_member_schema_to_dto(team_member)

    async def update_team_member(
        self, user_id: UUID, dto: TeamMemberUpdateDTO
    ) -> TeamMemberReadDTO:
        """Change a team member's role.

        Args:
            user_id: Manager performing the update.
            dto: Target user, team id, and replacement role.

        Returns:
            TeamMemberReadDTO: Updated membership row.

        Raises:
            TeamAccessDeniedError: If the manager cannot assign the role, cannot
                manage the team, or attempts to change an admin.
            TeamMemberNotFoundError: If the target membership does not exist.
            TeamNotFoundError: If role checking cannot load the team.
        """
        await self._check_role(user_id, dto.team_id, dto.role, dto.user_id)
        if not await self.permission_checker.can_manage_team(user_id, dto.team_id):
            raise TeamAccessDeniedError(
                "You do not have permission to add a team member"
            )
        team_member = await self.team_repository.get_team_member_if_accessible(
            dto.user_id, dto.team_id
        )

        # TODO Add validation for role change e.g. owner cannot be removed, owner cannot be demoted to member, etc.

        if team_member is None:
            raise TeamMemberNotFoundError("Team member not found")
        if team_member.role == Role.ADMIN:
            raise TeamAccessDeniedError("You do not have permission to update an admin")
        team_member.role = dto.role
        await self.team_repository.update_team_member(team_member)
        await self.permission_service.update_user_team_role_permissions(
            dto.user_id, dto.team_id, dto.role
        )
        await self.db.commit()
        return self.team_mapper.team_member_schema_to_dto(team_member)

    async def remove_team_member(self, user_id: UUID, dto: TeamMemberDeleteDTO) -> None:
        """Remove a member from a team and revoke team permissions.

        Members may remove themselves without manage permission; managers can remove
        other non-owner, non-admin members.

        Args:
            user_id: User performing the removal.
            dto: Target user and team id.

        Returns:
            None: Membership and permission rows are removed and committed.

        Raises:
            TeamNotFoundError: If the team does not exist.
            TeamAccessDeniedError: If the target is the owner/admin or the requester
                cannot remove the member.
            TeamMemberNotFoundError: If the target membership does not exist.
        """
        team_id = dto.team_id
        try:
            team = await self.team_repository.get_by_id_with_owner(team_id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")

        if str(dto.user_id) == str(team.owner_id):
            raise TeamAccessDeniedError("Cannot remove the team owner")

        team_member = await self.team_repository.get_team_member_if_accessible(
            dto.user_id, team_id
        )
        if team_member is None:
            raise TeamMemberNotFoundError("Team member not found")
        if team_member.role == Role.ADMIN:
            raise TeamAccessDeniedError("You do not have permission to remove an admin")

        is_self = str(user_id) == str(dto.user_id)
        can_manage = await self.permission_checker.can_manage_team(user_id, team_id)
        if not is_self and not can_manage:
            raise TeamAccessDeniedError(
                "You do not have permission to remove a team member"
            )
        if is_self and not can_manage:
            # Member may leave the team without manage_team
            pass

        await self.team_repository.delete_team_member(dto.user_id, team_id)
        await self.permission_service.remove_user_from_team_permissions(
            dto.user_id, team_id
        )
        await self.db.commit()
