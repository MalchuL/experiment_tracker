from typing import List
from uuid import UUID
from lib.types import UUID_TYPE
from models import Team


def is_team_accessible(
    team_id: UUID_TYPE, accessible_team_ids: List[UUID | Team]
) -> bool:
    if not accessible_team_ids:
        return False

    return str(team_id) in [str(get_team_id(team)) for team in accessible_team_ids]


def get_team_id(team: UUID | Team) -> UUID:
    if isinstance(team, Team):
        return team.id
    return team
