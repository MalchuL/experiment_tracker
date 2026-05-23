"""Click CLI group for ``experiment-tracker`` (init, whoami, ping, run)."""

from __future__ import annotations

import importlib.metadata
import json
from typing import cast

import click

from ..api_access import ExpTrackerApiAccess
from ..client.domain.users.dto import UserResponse
from ..config import save_config
from ..error import ExpTrackerConfigError
from ..settings import get_cli_init_defaults
from .run import run_command


def _get_value(value: str | None, prompt: str, secret: bool = False) -> str:
    """Return provided value or prompt the user for input.

    Args:
        value: Optional value to use as-is.
        prompt: Prompt displayed when value is missing.
        secret: Reserved for future masked input behavior.

    Returns:
        Resolved string value.
    """
    if value:
        return value
    return input(prompt).strip()


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
def init_command(
    base_url: str | None,
    api_prefix: str | None,
    api_token: str | None,
) -> None:
    """Store base URL, API prefix, and API token for later SDK use."""
    defaults = get_cli_init_defaults()
    resolved_base = _get_value(
        base_url,
        f"Base URL (default: {defaults.default_base_url}): ",
    )
    if not resolved_base:
        resolved_base = defaults.default_base_url
    if api_prefix is None:
        entered_prefix = _get_value(
            None,
            f"API prefix (default: {defaults.default_api_prefix}, empty for none): ",
        )
        resolved_prefix = (
            entered_prefix if entered_prefix != "" else defaults.default_api_prefix
        )
    else:
        resolved_prefix = api_prefix
    resolved_token = _get_value(api_token, "API token: ")
    config_path = save_config(
        base_url=resolved_base,
        api_token=resolved_token,
        api_prefix=resolved_prefix,
    )
    click.echo(f"Config saved to {config_path}")


@cli.command("whoami", short_help="Validate token and print profile")
def whoami_command() -> None:
    """Call ``GET /users/me/profile`` using saved credentials."""
    try:
        access = ExpTrackerApiAccess.instance()
        client = access.get_request_client()
        registry = access.get_api_requests_registry()
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
    """Request ``GET /`` on the configured API base URL."""
    try:
        access = ExpTrackerApiAccess.instance()
        client = access.get_request_client()
        code = client.probe_http_status("GET", "/")
    except ExpTrackerConfigError as exc:
        raise click.UsageError(
            "Config not found. Run `experiment-tracker init`."
        ) from exc
    click.echo(f"Status: {code}")


cli.add_command(run_command)
