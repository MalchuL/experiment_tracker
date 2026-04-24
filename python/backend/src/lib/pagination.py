from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Sequence, TypeVar

from pydantic import BaseModel, Field

from lib.dto_config import model_config

T = TypeVar("T")
U = TypeVar("U")

# Upper bound for list pagination (`limit` query param and `ListOptions.limit`).
MAX_LIST_PAGE_SIZE = 100


class ListOptions(BaseModel):
    """Limit/offset pagination parameters used inside backend services.

    This model is the repository-facing abstraction for pagination. Controllers
    and services can pass `ListOptions` around without depending on
    Advanced Alchemy's `LimitOffset` type.
    """

    limit: int = Field(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE)
    offset: int = Field(default=0, ge=0)


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """A paginated slice of items plus pagination metadata.

    Attributes:
        data: Items for the current page.
        has_next: Whether another page exists after the current slice.
        total: Total number of items matching the query (before pagination).
    """

    data: list[T]
    has_next: bool
    total: int

    @property
    def size(self) -> int:
        """Return the number of items in the current page."""
        return len(self.data)

    def map(self, mapper: Callable[[T], U]) -> Page[U]:
        """Transform page items while preserving pagination metadata."""
        return Page(
            data=[mapper(item) for item in self.data],
            has_next=self.has_next,
            total=self.total,
        )


def paginate_sequence(items: Sequence[T], options: ListOptions) -> Page[T]:
    """Paginate an in-memory sequence.

    Prefer paginating at the data source when possible. This helper is intended
    for cases where items are already materialized in memory, such as
    controller-local computed lists or compatibility paths that cannot yet push
    pagination deeper into storage.
    """

    start = options.offset
    end = start + options.limit
    total = len(items)
    return Page(
        data=list(items[start:end]),
        has_next=end < total,
        total=total,
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Public API pagination envelope used by backend responses."""

    data: list[T]
    has_next: bool = False
    size: int = 0
    total: int = 0

    model_config = model_config()

    @classmethod
    def from_page(cls, page: Page[T]) -> PaginatedResponse[T]:
        """Build a response envelope from an internal `Page`."""
        return cls(
            data=page.data,
            has_next=page.has_next,
            size=page.size,
            total=page.total,
        )
