"""Shared DTO model configuration for object_storage response models."""

from __future__ import annotations

from pydantic import AliasGenerator, ConfigDict
from pydantic.alias_generators import to_camel


def model_config() -> ConfigDict:
    """Return the default DTO model configuration.

    Returns:
        Pydantic ``ConfigDict`` that forbids unknown fields, supports population
        by field name, and enables snake_case <-> camelCase aliases.
    """

    return ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=to_camel,
            serialization_alias=to_camel,
        ),
        extra="forbid",
        populate_by_name=True,
    )
