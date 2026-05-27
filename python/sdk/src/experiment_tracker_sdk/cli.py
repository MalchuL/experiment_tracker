"""Compatibility entrypoint for the ``experiment-tracker`` console script."""

from __future__ import annotations


def main() -> None:
    """CLI entrypoint for experiment-tracker commands.

    Example:
        experiment-tracker init --base-url URL --api-prefix /api --api-token <TOKEN>
    """
    from click.exceptions import Abort, ClickException, Exit

    from experiment_tracker_sdk.console.commands import cli

    try:
        rv = cli.main(standalone_mode=False)
    except Exit as e:
        raise SystemExit(e.exit_code) from e
    except Abort:
        raise SystemExit(1) from None
    except ClickException as e:
        e.show()
        raise SystemExit(e.exit_code) from e

    if rv not in (None, 0):
        raise SystemExit(rv)


if __name__ == "__main__":
    main()
