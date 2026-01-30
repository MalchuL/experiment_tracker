import argparse
import json
from typing import Optional

import httpx

from .config import load_config, save_config


def _get_value(value: Optional[str], prompt: str, secret: bool = False) -> str:
    if value:
        return value
    return input(prompt).strip()


def cmd_init(args: argparse.Namespace) -> None:
    base_url = _get_value(args.base_url, "Base URL: ")
    api_token = _get_value(args.api_token, "API token: ")
    save_config(base_url=base_url, api_token=api_token)
    print("Config saved.")


def cmd_whoami(args: argparse.Namespace) -> None:
    config = load_config()
    if config is None:
        raise SystemExit("Config not found. Run `experiment-tracker init`.")
    with httpx.Client(
        base_url=config.base_url,
        headers={"Authorization": f"Bearer {config.api_token}"},
    ) as client:
        response = client.get("/users/me/profile")
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))


def cmd_ping(args: argparse.Namespace) -> None:
    config = load_config()
    if config is None:
        raise SystemExit("Config not found. Run `experiment-tracker init`.")
    with httpx.Client(base_url=config.base_url) as client:
        response = client.get("/")
        print(f"Status: {response.status_code}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="experiment-tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Save SDK configuration")
    init_parser.add_argument("--base-url", dest="base_url")
    init_parser.add_argument("--api-token", dest="api_token")
    init_parser.set_defaults(func=cmd_init)

    whoami_parser = subparsers.add_parser("whoami", help="Validate token")
    whoami_parser.set_defaults(func=cmd_whoami)

    ping_parser = subparsers.add_parser("ping", help="Check API availability")
    ping_parser.set_defaults(func=cmd_ping)

    args = parser.parse_args()
    args.func(args)
