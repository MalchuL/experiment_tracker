from __future__ import annotations

import re
from urllib.parse import unquote


def parse_content_disposition(header: str | None) -> str | None:
    """Extract filename from a Content-Disposition header value.

    Handles plain ``filename="foo.png"`` and RFC 5987
    ``filename*=UTF-8''foo%20bar.png`` encodings.
    """
    if not header:
        return None
    m = re.search(r"filename\*\s*=\s*[^']*''(.+?)(?:;|$)", header, re.IGNORECASE)
    if m:
        return unquote(m.group(1).strip())
    m = re.search(r'filename\s*=\s*"?([^";]+)"?', header, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None
