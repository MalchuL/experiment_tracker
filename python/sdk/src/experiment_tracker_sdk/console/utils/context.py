from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunCliContext:
    """Context built by ``experiment-tracker run`` for bootstrap hooks."""

    # ``--project`` when provided; reserved for future tracker bootstrap (e.g.
    # default project). Never forwarded to the target script's ``sys.argv``.
    project: str | None

    # ``--team`` when provided; reserved for future tracker bootstrap alongside
    # ``--project``. Never forwarded to the target script's ``sys.argv``.
    team: str | None

    # True when ``--offline`` was passed; reserved for future tracker bootstrap
    # (e.g. disable network). Never forwarded to the target script's ``sys.argv``.
    offline: bool

    # Path string used as ``sys.argv[0]`` so the script sees the same argv shape as
    # a direct ``python SCRIPT`` launch (often a relative path as typed by the user).
    script_argv0: str

    # Absolute path of the script file passed to ``runpy.run_path`` so loading does
    # not depend on the process CWD after any chdir during bootstrap.
    script_resolved_path: str
