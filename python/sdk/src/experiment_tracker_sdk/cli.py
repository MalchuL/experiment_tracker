import argparse
import json
from typing import Optional

import httpx

from .config import compose_base_url, load_config, save_config


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_API_PREFIX = "/api"


def _get_value(value: Optional[str], prompt: str, secret: bool = False) -> str:
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


def cmd_init(args: argparse.Namespace) -> None:
    """Handle `experiment-tracker init` to store SDK config.

    Args:
        args: Parsed CLI arguments with base_url and api_token.
    """
    base_url = _get_value(args.base_url, f"Base URL (default: {DEFAULT_BASE_URL}): ")
    if not base_url:
        base_url = DEFAULT_BASE_URL
    if args.api_prefix is None:
        entered_prefix = _get_value(
            None, f"API prefix (default: {DEFAULT_API_PREFIX}, empty for none): "
        )
        api_prefix = entered_prefix if entered_prefix != "" else DEFAULT_API_PREFIX
    else:
        api_prefix = args.api_prefix
    api_token = _get_value(args.api_token, "API token: ")
    config_path = save_config(
        base_url=base_url,
        api_token=api_token,
        api_prefix=api_prefix,
    )
    print(f"Config saved to {config_path}")


def cmd_whoami(args: argparse.Namespace) -> None:
    """Validate the configured token and print the user profile.

    Args:
        args: Parsed CLI arguments (unused).
    """
    config = load_config()
    if config is None:
        raise SystemExit("Config not found. Run `experiment-tracker init`.")
    with httpx.Client(
        base_url=compose_base_url(config.base_url, config.api_prefix),
        headers={"Authorization": f"Bearer {config.api_token}"},
    ) as client:
        response = client.get("/users/me/profile")
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))


def cmd_ping(args: argparse.Namespace) -> None:
    """Ping the backend base URL to check availability.

    Args:
        args: Parsed CLI arguments (unused).
    """
    config = load_config()
    if config is None:
        raise SystemExit("Config not found. Run `experiment-tracker init`.")
    with httpx.Client(base_url=compose_base_url(config.base_url, config.api_prefix)) as client:
        response = client.get("/")
        print(f"Status: {response.status_code}")


def main() -> None:
    """CLI entrypoint for experiment-tracker commands.

    Example:
        experiment-tracker init --base-url http://127.0.0.1:8000 --api-prefix /api --api-token <TOKEN>
    """
    parser = argparse.ArgumentParser(prog="experiment-tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Save SDK configuration")
    init_parser.add_argument("--base-url", dest="base_url")
    init_parser.add_argument("--api-prefix", dest="api_prefix")
    init_parser.add_argument("--api-token", dest="api_token")
    init_parser.set_defaults(func=cmd_init)

    whoami_parser = subparsers.add_parser("whoami", help="Validate token")
    whoami_parser.set_defaults(func=cmd_whoami)

    ping_parser = subparsers.add_parser("ping", help="Check API availability")
    ping_parser.set_defaults(func=cmd_ping)

    args = parser.parse_args()
    args.func(args)
