"""HTTP routes under ``/teams``: team CRUD, members, invites, and lookup."""

from uuid import UUID

from api.routes.service_dependencies import get_team_service
from fastapi import APIRouter, Depends, HTTPException, Query
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions, PaginatedResponse

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from models import User
from domain.rbac.permissions.team import TeamActions

from .dto import (
    TeamCreateDTO,
    TeamDeleteResponseDTO,
    TeamListItemDTO,
    TeamMemberCreateDTO,
    TeamMemberDeleteDTO,
    TeamMemberReadDTO,
    TeamMemberUpdateDTO,
    TeamMemberWithUserDTO,
    TeamReadDTO,
    TeamUpdateDTO,
    TeamUserLookupDTO,
)
from .errors import (
    TeamAccessDeniedError,
    TeamMemberAlreadyExistsError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
)
from .service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


def _raise_team_http_error(error: Exception) -> None:
    """Translate team domain errors into HTTP exceptions.

    Args:
        error: Exception raised by ``TeamService``.

    Raises:
        HTTPException: ``403`` for access denial, ``404`` for missing teams or
            members, ``409`` for duplicate members, and ``400`` for other team
            errors.
    """
    if isinstance(error, TeamAccessDeniedError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, (TeamNotFoundError, TeamMemberNotFoundError)):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, TeamMemberAlreadyExistsError):
        raise HTTPException(status_code=409, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.get("", response_model=PaginatedResponse[TeamListItemDTO])
async def list_teams(
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.VIEW_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """List teams visible to the current user.

    Args:
        limit: Maximum number of teams to return.
        offset: Number of teams to skip.
        user: Authenticated user requesting teams.
        _: API-token scope guard requiring team view access.
        team_service: Team application service dependency.

    Returns:
        PaginatedResponse[TeamListItemDTO]: Teams plus per-row project creation
        capability.

    Raises:
        HTTPException: ``403`` or ``400`` if the service rejects the request.
    """
    try:
        page = await team_service.list_teams(
            user.id, list_options=ListOptions(limit=limit, offset=offset)
        )
        return PaginatedResponse[TeamListItemDTO].from_page(page)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.get("/{team_id}/members", response_model=list[TeamMemberWithUserDTO])
async def list_team_members(
    team_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.VIEW_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """List members of a team.

    Args:
        team_id: Team identifier.
        user: Authenticated user requesting members.
        _: API-token scope guard requiring team view access.
        team_service: Team application service dependency.

    Returns:
        list[TeamMemberWithUserDTO]: Owner and member rows with user metadata.

    Raises:
        HTTPException: ``403`` for access denial, ``404`` for missing team, or
            ``400`` for other service errors.
    """
    try:
        return await team_service.list_team_members(user.id, team_id)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.get("/{team_id}/users/lookup", response_model=TeamUserLookupDTO)
async def lookup_team_user_by_email(
    team_id: UUID,
    email: str = Query(..., min_length=1, max_length=320),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.MANAGE_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """Look up an active user by email before adding them to a team.

    Args:
        team_id: Team where the user would be managed.
        email: Email address to normalize and search.
        user: Authenticated manager performing the lookup.
        _: API-token scope guard requiring team manage access.
        team_service: Team application service dependency.

    Returns:
        TeamUserLookupDTO: Basic user identity for confirmation.

    Raises:
        HTTPException: ``403`` for insufficient manage permission, ``404`` for
            missing team or user, and ``400`` for other service errors.
    """
    try:
        return await team_service.lookup_user_by_email(user.id, team_id, email)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.get("/{team_id}", response_model=TeamReadDTO)
async def get_team(
    team_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.VIEW_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """Return a team visible to the current user.

    Args:
        team_id: Team identifier.
        user: Authenticated user requesting the team.
        _: API-token scope guard requiring team view access.
        team_service: Team application service dependency.

    Returns:
        TeamReadDTO: Team metadata.

    Raises:
        HTTPException: ``403`` for access denial, ``404`` for missing team, or
            ``400`` for other service errors.
    """
    try:
        return await team_service.get_team(user.id, team_id)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.post("", response_model=TeamReadDTO)
async def create_team(
    data: TeamCreateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.MANAGE_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """Create a new team owned by the current user.

    Args:
        data: Team create payload.
        user: Authenticated user who becomes the owner/admin.
        _: API-token scope guard requiring team manage access.
        team_service: Team application service dependency.

    Returns:
        TeamReadDTO: Created team metadata.

    Raises:
        HTTPException: ``400`` for validation or persistence errors.
    """
    try:
        return await team_service.create_team(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.patch("", response_model=TeamReadDTO)
async def update_team(
    data: TeamUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.MANAGE_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """Update team metadata.

    Args:
        data: Update payload including the team id.
        user: Authenticated team manager.
        _: API-token scope guard requiring team manage access.
        team_service: Team application service dependency.

    Returns:
        TeamReadDTO: Updated team metadata.

    Raises:
        HTTPException: ``403`` for insufficient permission, ``404`` for missing team,
            and ``400`` for other service errors.
    """
    try:
        return await team_service.update_team(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


# Member routes MUST come before /{team_id} route to avoid routing conflicts
@router.post("/members", response_model=TeamMemberReadDTO)
async def add_team_member(
    data: TeamMemberCreateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.MANAGE_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """Add a user to a team with a role.

    Args:
        data: Target user, team id, and role.
        user: Authenticated manager adding the member.
        _: API-token scope guard requiring team manage access.
        team_service: Team application service dependency.

    Returns:
        TeamMemberReadDTO: Persisted team-member row.

    Raises:
        HTTPException: ``403`` for role-management denial, ``409`` for duplicates,
            ``404`` for missing team/user rows, and ``400`` for other errors.
    """
    try:
        return await team_service.add_team_member(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.patch("/members", response_model=TeamMemberReadDTO)
async def update_team_member(
    data: TeamMemberUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.MANAGE_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """Update an existing team member's role.

    Args:
        data: Target user, team id, and replacement role.
        user: Authenticated manager changing the role.
        _: API-token scope guard requiring team manage access.
        team_service: Team application service dependency.

    Returns:
        TeamMemberReadDTO: Updated membership row.

    Raises:
        HTTPException: ``403`` for role-management denial, ``404`` for missing member,
            and ``400`` for other service errors.
    """
    try:
        return await team_service.update_team_member(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.delete("/members")
async def remove_team_member(
    data: TeamMemberDeleteDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.MANAGE_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """Remove a member from a team.

    Args:
        data: Target user and team id.
        user: Authenticated user removing the member or leaving the team.
        _: API-token scope guard requiring team manage access.
        team_service: Team application service dependency.

    Returns:
        dict[str, bool]: ``{"success": True}`` after removal.

    Raises:
        HTTPException: ``403`` for access denial, ``404`` for missing team/member, or
            ``400`` for other service errors.
    """
    try:
        await team_service.remove_team_member(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)
    return {"success": True}


@router.delete("/{team_id}", response_model=TeamDeleteResponseDTO)
async def delete_team(
    team_id: UUID,
    detailed: bool = Query(
        False,
        description=(
            "When true, include full per-step ``results``. "
            "When false (default), ``results`` is empty and ``resultCount`` counts successes."
        ),
    ),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.DELETE_TEAM)),
    team_service: TeamService = Depends(get_team_service),
):
    """Delete a team and clean up its projects.

    Args:
        team_id: Team identifier to delete.
        detailed: Whether to include full cleanup result payloads.
        user: Authenticated user deleting the team.
        _: API-token scope guard requiring team delete access.
        team_service: Team application service dependency.

    Returns:
        TeamDeleteResponseDTO: Structured cleanup outcome for project satellites,
        project rows, and the team row.

    Raises:
        HTTPException: ``403`` for insufficient permission, ``404`` for missing team,
            and ``400`` for cleanup or repository errors.
    """
    try:
        return await team_service.delete_team(user.id, team_id, detailed=detailed)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)
