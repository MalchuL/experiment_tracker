from __future__ import annotations

import importlib.util

from .bootstrap import register_run_bootstrap_hook
from .context import RunCliContext

_defaults_registered = False


def _tensorboard_bootstrap(_ctx: RunCliContext) -> None:
    """TensorBoard / TensorBoardX setup for in-process ``run``.

    When ``tensorboard`` or ``tensorboardX`` is installed, warm-import it as an
    extension point for future SummaryWriter integration. Both dependencies stay
    optional.
    """
    for name in ("tensorboard", "tensorboardX"):
        if importlib.util.find_spec(name) is None:
            continue
        importlib.import_module(name)  # noqa: F401 — side effect / warm import


def register_default_tensorboard_hooks() -> None:
    """Idempotently register built-in TensorBoard bootstrap behavior."""
    global _defaults_registered
    if _defaults_registered:
        return
    _defaults_registered = True
    register_run_bootstrap_hook(_tensorboard_bootstrap)
