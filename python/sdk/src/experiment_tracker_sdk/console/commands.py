"""Click CLI group for ``experiment-tracker`` (init, whoami, ping, run)."""

from __future__ import annotations

import importlib.metadata
import json

import click
import httpx

from ..config import compose_base_url, load_config, save_config
from ..settings import get_exp_tracker_settings
from .run import run_command


def _cli_init_defaults() -> tuple[str, str]:
    s = get_exp_tracker_settings()
    return s.default_base_url, s.default_api_prefix


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
    default_base_url, default_api_prefix = _cli_init_defaults()
    resolved_base = _get_value(
        base_url,
        f"Base URL (default: {default_base_url}): ",
    )
    if not resolved_base:
        resolved_base = default_base_url
    if api_prefix is None:
        entered_prefix = _get_value(
            None,
            f"API prefix (default: {default_api_prefix}, empty for none): ",
        )
        resolved_prefix = (
            entered_prefix if entered_prefix != "" else default_api_prefix
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
    config = load_config()
    if config is None:
        raise click.UsageError("Config not found. Run `experiment-tracker init`.")
    with httpx.Client(
        base_url=compose_base_url(config.base_url, config.api_prefix),
        headers={"Authorization": f"Bearer {config.api_token}"},
    ) as client:
        response = client.get("/users/me/profile")
        response.raise_for_status()
        click.echo(json.dumps(response.json(), indent=2))


@cli.command("ping", short_help="Check API availability")
def ping_command() -> None:
    """Request ``GET /`` on the configured API base URL."""
    config = load_config()
    if config is None:
        raise click.UsageError("Config not found. Run `experiment-tracker init`.")
    with httpx.Client(
        base_url=compose_base_url(config.base_url, config.api_prefix),
    ) as client:
        response = client.get("/")
        click.echo(f"Status: {response.status_code}")


cli.add_command(run_command)
