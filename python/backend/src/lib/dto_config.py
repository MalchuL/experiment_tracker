"""Shared API JSON naming: **Python fields use snake_case**; **HTTP JSON uses camelCase keys**.

DTOs that set ``model_config = model_config()`` use Pydantic's ``AliasGenerator`` with
``to_camel`` for both validation and serialization. Effects:

- **Source code**: declare ``display_name``, ``user_id``, ``is_team_owner``, etc.
- **Wire format**: JSON property names are camelCase — ``displayName``, ``userId``,
  ``isTeamOwner``. Those are the names in quoted strings in JSON bodies/responses and in
  OpenAPI ``model_json_schema()`` / Swagger ``properties``.
- **FastAPI**: Encoders serialize response models with aliases, matching
  ``model_dump(mode="json", by_alias=True)``.

Examples (Python attribute → JSON key):

- ``display_name`` → ``displayName``
- ``user_id`` / ``team_id`` / ``member_id`` → ``userId`` / ``teamId`` / ``memberId``
- ``is_team_owner`` → ``isTeamOwner``
- ``can_create_project`` → ``canCreateProject``
- ``created_at`` / ``owner_id`` → ``createdAt`` / ``ownerId``

Single-word fields stay as-is: ``id``, ``name``, ``email``, ``role``.

``populate_by_name=True`` keeps accepting Python field names when validating dicts built
inside the server; **external clients** should send camelCase keys for request bodies.

**Used by** any module that imports ``model_config`` from this file (projects, teams,
hypotheses, experiments, metrics, members, dashboard, rbac, api_tokens, artifacts,
pagination, auth change-password, admin, …). User DTOs in ``domain/team/users/dto.py`` merge
this with FastAPI Users base ``model_config`` so ``/users`` routes match the same rules.
"""

from __future__ import annotations

from pydantic import ConfigDict, AliasGenerator
from pydantic.alias_generators import to_camel


def model_config() -> ConfigDict:
    return ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=to_camel,
            serialization_alias=to_camel,
        ),
        extra="forbid",
        populate_by_name=True,
    )
