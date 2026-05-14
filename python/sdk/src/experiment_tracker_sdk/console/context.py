from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunCliContext:
    """Wrapper-side context available to bootstrap hooks before ``runpy``."""

    project: str | None
    offline: bool
    script_argv0: str
    script_resolved_path: str
