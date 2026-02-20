from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Result(Generic[T]):
    """
    Result of a plugin execution.
    If force_return is True, the result will override the default result.
    """

    value: T
    force_return: bool = False
