from typing import Dict, Iterable

from models import TeamRole


class TeamActions:
    CREATE_PROJECT = "projects.create"
    DELETE_PROJECT = "projects.delete"
    VIEW_PROJECT = "projects.view"
    MANAGE_TEAM = "teams.manage"
    DELETE_TEAM = "teams.delete"
    VIEW_TEAM = "teams.view"


TEAM_ACTIONS = (
    TeamActions.CREATE_PROJECT,
    TeamActions.DELETE_PROJECT,
    TeamActions.VIEW_PROJECT,
    TeamActions.MANAGE_TEAM,
    TeamActions.DELETE_TEAM,
    TeamActions.VIEW_TEAM,
)


def _build_permissions(allowed_actions: Iterable[str]) -> Dict[str, bool]:
    allowed_set = set(allowed_actions)
    return {action: action in allowed_set for action in TEAM_ACTIONS}


def role_to_team_permissions(role: TeamRole) -> Dict[str, bool]:
    match role:
        case TeamRole.OWNER:
            return _build_permissions(TEAM_ACTIONS)
        case TeamRole.ADMIN:
            return _build_permissions(TEAM_ACTIONS)
        case TeamRole.MEMBER:
            allowed = {TeamActions.VIEW_PROJECT, TeamActions.VIEW_TEAM}
            return _build_permissions(allowed)
        case TeamRole.VIEWER:
            allowed = {TeamActions.VIEW_PROJECT, TeamActions.VIEW_TEAM}
            return _build_permissions(allowed)
