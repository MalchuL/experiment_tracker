"""Pydantic defaults for scalars_service HTTP responses (snake_case fields, camelCase JSON)."""

from __future__ import annotations

from pydantic import AliasGenerator, ConfigDict
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
