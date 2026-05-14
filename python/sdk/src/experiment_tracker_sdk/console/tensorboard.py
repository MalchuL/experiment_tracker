from __future__ import annotations

import importlib.util

from .bootstrap import register_run_bootstrap_hook
from .context import RunCliContext

_defaults_registered = False


def _tensorboard_bootstrap(_ctx: RunCliContext) -> None:
    """TensorBoard-related setup for in-process ``run``.

    When ``tensorboard`` is installed, this hook is the extension point for
    future SummaryWriter integration. Importing the package here keeps the
    dependency optional.
    """
    if importlib.util.find_spec("tensorboard") is None:
        return
    importlib.import_module("tensorboard")  # noqa: F401 — side effect / warm import


def register_default_tensorboard_hooks() -> None:
    """Idempotently register built-in TensorBoard bootstrap behavior."""
    global _defaults_registered
    if _defaults_registered:
        return
    _defaults_registered = True
    register_run_bootstrap_hook(_tensorboard_bootstrap)
