"""Hashing helpers shared by SDK and backend services."""

from __future__ import annotations

import hashlib
from pathlib import Path
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


def compute_file_sha256_hexdigest(
    path: str | Path, *, chunk_size: int = 1024 * 1024
) -> str:
    """Return SHA-256 hex digest for a file without loading it into memory.

    Args:
        path: Local filesystem path to the file that should be hashed.
        chunk_size: Number of bytes to read per iteration. The default is 1 MiB,
            which keeps memory bounded while avoiding excessive read calls.

    Returns:
        Hex-encoded SHA-256 digest for the full file contents.
    """
    hasher = create_sha256_hasher()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
