"""Thread-pool helpers for parallel SDK work."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def default_parallel_worker_count() -> int:
    """Return the default worker count: ``min(4, cpu_count)``."""
    return min(4, os.cpu_count() or 1)


class ParallelTaskRunner:
    """Execute independent callables in a bounded thread pool."""

    def __init__(self, *, max_workers: int | None = None) -> None:
        self._max_workers = (
            default_parallel_worker_count() if max_workers is None else max_workers
        )

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def map(self, func: Callable[[T], R], items: Iterable[T]) -> list[R]:
        """Apply ``func`` to each item, preserving input order."""
        work = list(items)
        if not work:
            return []
        if self._max_workers <= 1 or len(work) == 1:
            return [func(item) for item in work]
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            return list(executor.map(func, work))
