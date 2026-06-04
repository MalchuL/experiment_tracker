"""Click CLI group for ``experiment-tracker`` (init, whoami, ping, run)."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import click

from ..client.api_access import ExpTrackerApiAccess
from ..client.domain.health.dto import HealthCheckResponse
from ..client.domain.users.dto import UserResponse
from ..config import load_config, save_config
from ..constants import DEFAULT_API_PREFIX, DEFAULT_BASE_URL
from ..error import ExpTrackerConfigError
from ..settings import DEFAULT_CONFIG_DIR, get_exp_tracker_settings
from ..snapshot import (
    DEFAULT_IGNORE_FILES,
    create_exp_tracker_ignore,
    format_scan_summary,
    format_skipped_lines,
    scan_snapshot_files,
)
from .domains import DOMAIN_COMMANDS
from .run import run_command


def _get_value(
    value: str | None,
    prompt: str,
    *,
    default: str | None = None,
    display_default: str | None = None,
) -> str:
    """Return provided value or prompt the user for input.

    Args:
        value: Optional value to use as-is.
        prompt: Prompt displayed when value is missing.
        default: Optional prompt default used when input is empty.
        display_default: Optional value shown in the prompt instead of default.
        secret: Reserved for future masked input behavior.

    Returns:
        Resolved string value.
    """
    if value is not None:
        return value
    if default is None:
        return input(f"{prompt}: ").strip()
    shown_default = display_default if display_default is not None else default
    entered = input(f"{prompt} (default: {shown_default}): ").strip()
    return entered if entered else default


def _mask_token(token: str | None) -> str | None:
    if token is None:
        return None
    if len(token) <= 14:
        return "*" * len(token)
    return f"{token[:7]}{'*' * (len(token) - 14)}{token[-7:]}"


@dataclass(frozen=True)
class CliInitDefaults:
    """Resolved defaults for ``experiment-tracker init`` interactive prompts."""

    default_base_url: str
    default_api_prefix: str
    api_token: str | None


def _get_init_defaults() -> CliInitDefaults:
    settings = get_exp_tracker_settings()
    defaults = CliInitDefaults(
        default_base_url=settings.base_url or DEFAULT_BASE_URL,
        default_api_prefix=(
            settings.api_prefix
            if settings.api_prefix is not None
            else DEFAULT_API_PREFIX
        ),
        api_token=settings.api_token,
    )
    try:
        config = load_config()
    except (ExpTrackerConfigError, OSError, ValueError):
        return defaults
    return CliInitDefaults(
        default_base_url=config.base_url,
        default_api_prefix=config.api_prefix,
        api_token=config.api_token,
    )


def _create_exp_tracker_ignore(directory: str | Path, *, force: bool) -> Path:
    """Create the default tracker ignore file and convert path errors to Click.

    Args:
        directory: Directory where ``.exp_tracker_ignore`` should be created.
        force: Whether an existing ignore file should be overwritten.

    Returns:
        Path to the created or existing ignore file.
    """
    try:
        return create_exp_tracker_ignore(directory, force=force)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise click.ClickException(str(exc)) from exc


@click.group(
    "experiment-tracker",
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=(
        "The `run` subcommand executes a training script in-process (simple "
        "experiments only). See `experiment-tracker run --help`."
    ),
)
@click.version_option(
    importlib.metadata.version("experiment-tracker-sdk"),
    prog_name="experiment-tracker",
)
def cli() -> None:
    """Experiment Tracker SDK command-line interface."""


@cli.command("init", short_help="Save SDK configuration")
@click.option("--base-url", "base_url", default=None)
@click.option("--api-prefix", "api_prefix", default=None)
@click.option("--api-token", "api_token", default=None)
@click.option(
    "--create-ignore-file",
    is_flag=True,
    help="Also create .exp_tracker_ignore in the current directory.",
)
def init_command(
    base_url: str | None,
    api_prefix: str | None,
    api_token: str | None,
    create_ignore_file: bool,
) -> None:
    """Store base URL, API prefix, and API token for later SDK use."""
    defaults = _get_init_defaults()
    resolved_base = _get_value(
        base_url,
        "Base URL",
        default=defaults.default_base_url,
    )
    resolved_prefix = _get_value(
        api_prefix,
        "API prefix",
        default=defaults.default_api_prefix,
    )
    resolved_token = _get_value(
        api_token,
        "API token",
        default=defaults.api_token,
        display_default=_mask_token(defaults.api_token),
    )
    config_path = save_config(
        base_url=resolved_base,
        api_token=resolved_token,
        api_prefix=resolved_prefix,
    )
    click.echo(f"Config saved to {config_path}")
    if create_ignore_file:
        ignore_path = _create_exp_tracker_ignore(".", force=False)
        click.echo(f"Ignore file ready at {ignore_path}")


@cli.command("init-ignore", short_help="Create .exp_tracker_ignore")
@click.argument("directory", required=False, default=".")
@click.option("-f", "--force", is_flag=True, help="Overwrite an existing file.")
def init_ignore_command(directory: str, force: bool) -> None:
    """Create a default ``.exp_tracker_ignore`` for snapshot uploads."""
    ignore_path = _create_exp_tracker_ignore(directory, force=force)
    click.echo(f"Ignore file ready at {ignore_path}")


@cli.command("clean-config", short_help="Remove SDK configuration directory")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def clean_config_command(yes: bool) -> None:
    """Remove the SDK configuration directory."""
    if os.environ.get("EXP_TRACKER_CONFIG_PATH"):
        click.echo(
            "EXP_TRACKER_CONFIG_PATH is set; default config directory was not removed."
        )
        return
    config_dir = DEFAULT_CONFIG_DIR.expanduser()
    if not config_dir.exists():
        click.echo(f"Config directory does not exist: {config_dir}")
        return
    if not config_dir.is_dir():
        raise click.ClickException(
            f"Config path parent is not a directory: {config_dir}"
        )
    if not yes:
        click.confirm(f"Remove config directory {config_dir}?", abort=True)
    shutil.rmtree(config_dir)
    click.echo(f"Config directory removed: {config_dir}")


@cli.command("whoami", short_help="Validate token and print profile")
def whoami_command() -> None:
    """Call ``GET /users/me/profile`` using saved credentials."""
    try:
        access = ExpTrackerApiAccess.instance()
        client = access.request_client
        registry = access.api_requests_registry
        profile = cast(
            UserResponse,
            client.request(registry.users.get_my_profile()),
        )
    except ExpTrackerConfigError as exc:
        raise click.UsageError(
            "Config not found. Run `experiment-tracker init`."
        ) from exc
    click.echo(json.dumps(profile.model_dump(mode="json"), indent=2, default=str))


@cli.command("ping", short_help="Check API availability")
def ping_command() -> None:
    """Request ``GET /`` and print the healthcheck payload."""
    try:
        access = ExpTrackerApiAccess.instance()
        client = access.request_client
        registry = access.api_requests_registry
        health = cast(
            HealthCheckResponse,
            client.request(registry.health.get_healthcheck()),
        )
    except ExpTrackerConfigError as exc:
        raise click.UsageError(
            "Config not found. Run `experiment-tracker init`."
        ) from exc
    click.echo(json.dumps(health.model_dump(mode="json"), indent=2, default=str))


@cli.command("check-files", short_help="Preview snapshot files")
@click.argument("paths", nargs=-1)
@click.option(
    "--ignore-file",
    multiple=True,
    default=DEFAULT_IGNORE_FILES,
    show_default=True,
    help="Gitignore-compatible ignore file to apply. Repeat to use several.",
)
@click.option(
    "--root",
    default=None,
    metavar="ABSOLUTE_PATH",
    help="Absolute snapshot root. Defaults to discovery via ignore files.",
)
@click.option(
    "--show-skipped",
    is_flag=True,
    help="Also print skipped paths.",
)
@click.option(
    "--max-file-size",
    type=int,
    default=None,
    metavar="BYTES",
    help=(
        "Maximum file size to include. Defaults to settings; use -1 to disable."
    ),
)
def check_files_command(
    paths: tuple[str, ...],
    ignore_file: tuple[str, ...],
    root: str | None,
    show_skipped: bool,
    max_file_size: int | None,
) -> None:
    """Print files that would be included in ``ExpTracker.log_snapshot``."""
    scan = scan_snapshot_files(
        paths or ".",
        root=root,
        ignore_file=ignore_file,
        max_file_size=(
            get_exp_tracker_settings().snapshot_max_file_size
            if max_file_size is None
            else max_file_size
        ),
    )
    for line in format_scan_summary(scan):
        click.echo(line)
    if show_skipped and scan.skipped_details:
        click.echo("skipped paths:")
        for line in format_skipped_lines(scan.skipped_details):
            click.echo(line)


# Add the run command to the CLI via `experiment-tracker run`
cli.add_command(run_command)
for domain_command in DOMAIN_COMMANDS:
    cli.add_command(domain_command)
