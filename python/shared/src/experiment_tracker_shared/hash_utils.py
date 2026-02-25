"""Hashing helpers shared by SDK and backend services."""

from __future__ import annotations

import hashlib
from typing import Protocol


class Sha256Hasher(Protocol):
    def update(self, data: bytes) -> None: ...
    def hexdigest(self) -> str: ...


def create_sha256_hasher() -> Sha256Hasher:
    """Create a SHA-256 hasher for incremental updates."""
    return hashlib.sha256()


def compute_sha256_hexdigest(payload: bytes) -> str:
    """Return SHA-256 hex digest for bytes payload."""
    hasher = create_sha256_hasher()
    hasher.update(payload)
    return hasher.hexdigest()
