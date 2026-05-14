"""Console helpers for the `experiment-tracker` CLI (modular entrypoints)."""

from .bootstrap import register_run_bootstrap_hook
from .context import RunCliContext

__all__ = ["RunCliContext", "register_run_bootstrap_hook"]
