from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


@dataclass(frozen=True)
class ApiRequestSpec(Generic[ResponseT]):
    method: str
    endpoint: str
    request_payload: dict[str, Any] | BaseModel | None = None
    response_model: type[ResponseT] | None = None
    query_params: dict[str, Any] | None = None
    response_is_list: bool = False


# Backward-compatible alias.
RequestSpec = ApiRequestSpec
