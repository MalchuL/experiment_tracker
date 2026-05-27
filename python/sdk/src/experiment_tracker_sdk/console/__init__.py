from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    if name == "cli":
        from .commands import cli

        return cli
    raise AttributeError(name)

__all__ = ["cli"]
