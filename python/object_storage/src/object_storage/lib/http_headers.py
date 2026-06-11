"""HTTP response header helpers."""

from __future__ import annotations

from urllib.parse import quote


def attachment_content_disposition(filename: str) -> str:
    """Build a ``Content-Disposition`` attachment header safe for HTTP (latin-1).

    ASCII filenames use the plain ``filename="..."`` form. Non-ASCII names use
    RFC 5987 ``filename*=UTF-8''...`` so Starlette can encode the header value.
    """
    try:
        filename.encode("ascii")
    except UnicodeEncodeError:
        encoded = quote(filename, safe="")
        return f"attachment; filename*=UTF-8''{encoded}"
    escaped = filename.replace("\\", "\\\\").replace('"', '\\"')
    return f'attachment; filename="{escaped}"'
