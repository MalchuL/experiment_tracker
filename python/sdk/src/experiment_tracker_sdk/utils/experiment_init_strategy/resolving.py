from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class MultipleItemsResolveStrategy(Enum):
    """Strategy used when a name or ID resolves to multiple server objects."""

    ERROR = "error"
    FIRST = "first"
    LAST = "last"
    RANDOM = "random"
    OLDEST = "oldest"
    NEWEST = "newest"


@dataclass(frozen=True)
class MultipleResolvingContextObject:
    """Comparable wrapper for resolving multiple matching server objects.

    Args:
        item: Original SDK DTO object.
        date: Creation timestamp used by oldest/newest resolution strategies.
        id: Server object id converted to string.
        name: Server object name.
    """

    item: Any
    date: datetime
    id: str
    name: str
