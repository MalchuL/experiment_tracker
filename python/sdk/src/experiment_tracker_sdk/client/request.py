from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


@dataclass(frozen=True)
class RequestSpec(Generic[ResponseT]):
    method: str
    endpoint: str
    dto: dict[str, Any] | BaseModel | None = None
    returning_dto: type[ResponseT] | None = None
    params: dict[str, Any] | None = None
    returning_dto_is_list: bool = False
