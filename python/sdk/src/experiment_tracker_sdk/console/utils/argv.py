from __future__ import annotations


def split_on_first_double_dash(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Split argv tokens on the first ``--`` separator.

    Tokens after the first ``--`` are forwarded verbatim to the target script.
    """
    try:
        idx = tokens.index("--")
    except ValueError:
        return list(tokens), []
    return list(tokens[:idx]), list(tokens[idx + 1 :])
