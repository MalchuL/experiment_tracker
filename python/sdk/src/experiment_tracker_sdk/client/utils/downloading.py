from pathlib import Path
from io import BytesIO
from typing import Iterator


def dump_binary_content_to_path(
    content: bytes | BytesIO | Iterator[bytes],
    output_path: str | Path,
    content_filename: str | None = None,
) -> Path:
    """Dump binary content to a local file path."""
    destination = Path(output_path)
    if destination.is_dir():
        destination = destination / (content_filename or "download")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        # Copy the bytes content to the destination file.
        destination.write_bytes(content)
    elif isinstance(content, BytesIO):
        # Copy the BytesIO content to the destination file.
        destination.write_bytes(content.getvalue())
    else:
        # Stream iterator payload to disk without buffering whole file in memory.
        with destination.open("wb") as f:
            for chunk in content:
                f.write(chunk)
    return destination
