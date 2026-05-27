"""``experiment-tracker run`` — execute a script via ``runpy`` after bootstrap."""

from __future__ import annotations

import runpy
import sys
from datetime import datetime
from pathlib import Path

import click

from experiment_tracker_sdk.utils.experiment_init_strategy import InitParams

from .utils.argv import split_on_first_double_dash
from .utils.bootstrap import apply_run_bootstrap
from .utils.context import RunCliContext
from .utils.run.runner import RunSample
from ..utils.hooks.tensorboard import register_default_tensorboard_hooks

_EXPERIMENT_ARGV_META_KEY = "experiment_tracker_sdk.console.run.experiment_argv"
DEFAULT_PROJECT_NAME = "Default"

_SIMPLE_EXPERIMENTS_EPILOG = """\
This mode is for simple experiments only (single-process or lightly threaded
scripts, local debugging, one-off research). It is not a universal launcher for
distributed PyTorch, elastic multi-node jobs, or heavy multiprocessing.

The script runs in-process via runpy: bootstrap patches, imports, and sys
mutations persist in this interpreter after the run finishes.

Put arguments for your script after a lone ``--`` token, for example:
``experiment-tracker run train.py -- --epochs 10``.
"""


def _default_experiment_name() -> str:
    """Return the default run experiment name."""
    return f"Experiment {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"


class RunCommand(click.Command):
    """Splits argv on the first ``--`` before Click parses wrapper options.

    Tokens after the first ``--`` are stored on ``ctx.meta`` and forwarded to
    the target script unchanged. The left segment is parsed normally by Click
    (options + ``SCRIPT``), so unknown options such as ``--epochs`` fail unless
    they appear after ``--``.
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        wrapper, experiment = split_on_first_double_dash(args)
        if not wrapper:
            ctx.fail(
                "missing script: expected SCRIPT (and optional wrapper flags) "
                "before a `--` separator."
            )
        ctx.meta[_EXPERIMENT_ARGV_META_KEY] = experiment
        return super().parse_args(ctx, wrapper)


@click.command(
    cls=RunCommand,
    name="run",
    short_help="Run a Python script as __main__ (simple experiments only)",
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=_SIMPLE_EXPERIMENTS_EPILOG,
)
@click.option(
    "--project",
    default=None,
    metavar="NAME",
    help="Project name or id for future tracker bootstrap (wrapper only).",
)
@click.option(
    "--team",
    default=None,
    metavar="NAME",
    help="Team name or id for future tracker bootstrap (wrapper only).",
)
@click.option(
    "--experiment",
    default=None,
    metavar="NAME",
    help="Experiment name or id for tracker bootstrap (wrapper only).",
)
@click.option(
    "--offline",
    is_flag=True,
    help="Offline mode flag for future tracker bootstrap (wrapper only).",
)
@click.argument(
    "script",
    type=click.Path(
        exists=True,
        dir_okay=False,
        file_okay=True,
        path_type=Path,
    ),
)
def run_command(
    project: str | None,
    team: str | None,
    experiment: str | None,
    offline: bool,
    script: Path,
) -> None:
    """Run SCRIPT with ``__name__ == '__main__'`` after optional tracker bootstrap."""
    ctx = click.get_current_context()
    experiment_tokens: list[str] = list(
        ctx.meta.get(_EXPERIMENT_ARGV_META_KEY, ()),
    )
    script_display = str(script)
    resolved = str(script.resolve())
    register_default_tensorboard_hooks()
    runner: RunSample | None = None
    resolved_project = project or DEFAULT_PROJECT_NAME
    resolved_experiment = experiment or _default_experiment_name()
    if not offline:
        runner = RunSample()
        runner.init(
            experiment_name_or_id=resolved_experiment,
            project_name_or_id=resolved_project,
            team_name_or_id=team,
            init_params=InitParams(
                create_team_if_not_exists=team is not None,
                create_project_if_not_exists=True,
                create_experiment_if_not_exists=True,
            ),
        )
    ctx_obj = RunCliContext(
        project=resolved_project,
        team=team,
        experiment=resolved_experiment,
        runner=runner,
        offline=offline,
        script_argv0=script_display,
        script_resolved_path=resolved,
    )
    apply_run_bootstrap(ctx_obj)
    sys.argv = [script_display, *experiment_tokens]
    click.echo(f"Running script {resolved} with arguments context: {ctx_obj}")
    try:
        runpy.run_path(resolved, run_name="__main__")
    except BaseException:
        if runner is not None:
            runner.mark_failed()
        raise
    if runner is not None:
        runner.mark_completed()
