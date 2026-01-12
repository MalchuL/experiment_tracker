from pydantic import ConfigDict, AliasGenerator
from pydantic.alias_generators import to_camel


def model_config() -> ConfigDict:
    return ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=to_camel,  # Input: FirstName -> first_name
            serialization_alias=to_camel,  # Output: first_name -> firstName
        ),
        extra="forbid",
        populate_by_name=True,
    )
