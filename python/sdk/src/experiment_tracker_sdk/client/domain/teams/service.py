from typing import cast
from uuid import UUID

from .dto import (
    SuccessResponse,
    TeamCreateRequest,
    TeamListResponse,
    TeamMemberCreateRequest,
    TeamMemberDeleteRequest,
    TeamMemberResponse,
    TeamRole,
    TeamMemberUpdateRequest,
    TeamResponse,
    TeamUpdateRequest,
)
from .limits import truncate_team_description, truncate_team_name
from ...request_types import ApiRequestSpec


class TeamRequestSpecFactory:
    ENDPOINTS = {
        "get_all_teams": "/teams",
        "get_team": lambda team_id: f"/teams/{team_id}",
        "create_team": "/teams",
        "update_team": "/teams",
        "delete_team": lambda team_id: f"/teams/{team_id}",
        "add_team_member": "/teams/members",
        "update_team_member": "/teams/members",
        "remove_team_member": "/teams/members",
    }

    def get_all_teams(
        self,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ApiRequestSpec[TeamListResponse]:
        endpoint = cast(str, self.ENDPOINTS["get_all_teams"])
        query_params: dict[str, int] = {}
        if limit is not None:
            query_params["limit"] = limit
        if offset is not None:
            query_params["offset"] = offset
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=TeamListResponse,
            query_params=query_params or None,
        )

    def get_team(self, team_id: str | UUID) -> ApiRequestSpec[TeamResponse]:
        if isinstance(team_id, UUID):
            team_id = str(team_id)
        endpoint = cast(str, self.ENDPOINTS["get_team"](team_id))  # type: ignore[operator]
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=TeamResponse,
        )

    def create_team(
        self, name: str, description: str | None = None
    ) -> ApiRequestSpec[TeamResponse]:
        endpoint = cast(str, self.ENDPOINTS["create_team"])
        payload = TeamCreateRequest(
            name=truncate_team_name(name),
            description=truncate_team_description(description),
        )
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=TeamResponse,
        )

    def update_team(
        self, team_id: str | UUID, name: str, description: str | None = None
    ) -> ApiRequestSpec[TeamResponse]:
        if isinstance(team_id, UUID):
            team_id = str(team_id)
        endpoint = cast(str, self.ENDPOINTS["update_team"])
        payload = TeamUpdateRequest(
            id=team_id,
            name=truncate_team_name(name),
            description=truncate_team_description(description),
        )
        return ApiRequestSpec(
            method="PATCH",
            endpoint=endpoint,
            request_payload=payload,
            response_model=TeamResponse,
        )

    def delete_team(self, team_id: str | UUID) -> ApiRequestSpec[SuccessResponse]:
        if isinstance(team_id, UUID):
            team_id = str(team_id)
        endpoint = cast(str, self.ENDPOINTS["delete_team"](team_id))  # type: ignore[operator]
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=SuccessResponse,
        )

    def add_team_member(
        self, user_id: str | UUID, team_id: str | UUID, role: TeamRole
    ) -> ApiRequestSpec[TeamMemberResponse]:
        if isinstance(user_id, UUID):
            user_id = str(user_id)
        if isinstance(team_id, UUID):
            team_id = str(team_id)
        endpoint = cast(str, self.ENDPOINTS["add_team_member"])
        payload = TeamMemberCreateRequest(userId=user_id, teamId=team_id, role=role)
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=payload,
            response_model=TeamMemberResponse,
        )

    def update_team_member(
        self, user_id: str | UUID, team_id: str | UUID, role: TeamRole
    ) -> ApiRequestSpec[TeamMemberResponse]:
        if isinstance(user_id, UUID):
            user_id = str(user_id)
        if isinstance(team_id, UUID):
            team_id = str(team_id)
        endpoint = cast(str, self.ENDPOINTS["update_team_member"])
        payload = TeamMemberUpdateRequest(userId=user_id, teamId=team_id, role=role)
        return ApiRequestSpec(
            method="PATCH",
            endpoint=endpoint,
            request_payload=payload,
            response_model=TeamMemberResponse,
        )

    def remove_team_member(
        self, user_id: str | UUID, team_id: str | UUID
    ) -> ApiRequestSpec[SuccessResponse]:
        if isinstance(user_id, UUID):
            user_id = str(user_id)
        if isinstance(team_id, UUID):
            team_id = str(team_id)
        endpoint = cast(str, self.ENDPOINTS["remove_team_member"])
        payload = TeamMemberDeleteRequest(userId=user_id, teamId=team_id)
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            request_payload=payload,
            response_model=SuccessResponse,
        )


# Backward-compatible alias.
TeamService = TeamRequestSpecFactory
