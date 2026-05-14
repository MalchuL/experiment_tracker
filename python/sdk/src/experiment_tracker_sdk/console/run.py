from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

from .argv import split_on_first_double_dash
from .bootstrap import apply_run_bootstrap
from .context import RunCliContext
from .tensorboard import register_default_tensorboard_hooks

_SIMPLE_EXPERIMENTS_EPILOG = """\
This mode is for simple experiments only (single-process or lightly threaded
scripts, local debugging, one-off research). It is not a universal launcher for
distributed PyTorch, elastic multi-node jobs, or heavy multiprocessing.

The script runs in-process via runpy: bootstrap patches, imports, and sys
mutations persist in this interpreter after the run finishes.
"""


def build_run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="experiment-tracker run",
        allow_abbrev=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_SIMPLE_EXPERIMENTS_EPILOG,
    )
    parser.add_argument(
        "--project",
        default=None,
        metavar="NAME",
        help="Project name or id for future tracker bootstrap (wrapper only).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Offline mode flag for future tracker bootstrap (wrapper only).",
    )
    parser.add_argument(
        "script",
        help="Python file to execute with __name__ == '__main__'.",
    )
    return parser


def execute_run_cli(argv: list[str]) -> None:
    """Handle ``experiment-tracker run`` using ``argv`` shaped like ``sys.argv``."""
    if len(argv) < 2 or argv[1] != "run":
        raise SystemExit("Internal error: execute_run_cli expects a `run` subcommand.")
    tail = argv[2:]
    wrapper_tokens, experiment_tokens = split_on_first_double_dash(tail)
    parser = build_run_parser()
    separator_present = "--" in tail

    if not wrapper_tokens:
        parser.error(
            "missing script: expected SCRIPT (and optional wrapper flags) "
            "before a `--` separator."
        )

    if separator_present:
        args = parser.parse_args(wrapper_tokens)
    else:
        args, unknown = parser.parse_known_args(wrapper_tokens)
        if unknown:
            joined = " ".join(unknown)
            parser.error(
                "unrecognized wrapper arguments: "
                f"{joined}. "
                "Put script arguments after `--`, for example: "
                "`experiment-tracker run train.py -- --epochs 10`."
            )

    script_arg = args.script
    script_path = Path(script_arg).expanduser()
    if not script_path.is_file():
        parser.error(f"script does not exist or is not a file: {script_arg}")

    register_default_tensorboard_hooks()
    resolved = str(script_path.resolve())
    ctx = RunCliContext(
        project=args.project,
        offline=bool(args.offline),
        script_argv0=script_arg,
        script_resolved_path=resolved,
    )
    apply_run_bootstrap(ctx)
    sys.argv = [script_arg, *experiment_tokens]
    runpy.run_path(resolved, run_name="__main__")
