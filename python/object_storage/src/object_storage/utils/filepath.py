import re
from pathlib import PurePosixPath

_INVALID_PATH_CHARS_RE = re.compile(r"[:\x00-\x1f]")


def normalize_path(path: str) -> str:
    """Normalize the path to a relative path."""
    return path.strip().replace("\\", "/")


def validate_relative_path(path: str) -> bool:
    pure_path = PurePosixPath(path)
    if (
        path.startswith("/")
        or ".." in pure_path.parts
        or _INVALID_PATH_CHARS_RE.search(path) is not None
    ):
        return False
    return True
