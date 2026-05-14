from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import RunCliContext

RunBootstrapHook = Callable[["RunCliContext"], None]

_hooks: list[RunBootstrapHook] = []


def register_run_bootstrap_hook(hook: RunBootstrapHook) -> None:
    """Register a callable invoked before ``runpy.run_path`` for ``run``."""
    _hooks.append(hook)


def apply_run_bootstrap(ctx: RunCliContext) -> None:
    """Run all registered bootstrap hooks in registration order."""
    for hook in _hooks:
        hook(ctx)
