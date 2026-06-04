"""Progress bars (tqdm) for uploading and downloading file bytes.

Why this module exists
----------------------
When you log a checkpoint or dataset through the SDK, the HTTP library (httpx)
must send or receive raw bytes over the network. For large files that can take
a while, ``verbose=True`` shows a tqdm bar so you can see bytes moving.

Two different situations:

1. **Upload** — your file is already in RAM as ``bytes``. httpx reads it in
   small slices (like ``f.read(chunk_size)`` on a disk file). We wrap those
   bytes in :class:`ProgressBytesReader` so every slice updates the bar.

2. **Download** — the server sends the file in chunks. We pass each chunk
   through tqdm before your code writes it to disk.

You do not need to import this module unless you extend the SDK; the client
uses it when ``verbose=True``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO

if TYPE_CHECKING:
    from tqdm.std import tqdm as TqdmBar


def _get_tqdm() -> type[TqdmBar]:
    """Import tqdm only when verbose transfers are requested."""
    try:
        from tqdm import tqdm
    except ImportError as exc:
        raise ImportError(
            "verbose transfers require the 'tqdm' package; "
            "install with: pip install tqdm"
        ) from exc
    return tqdm


def content_length_from_headers(headers: Mapping[str, str]) -> int | None:
    """Read total download size from the HTTP ``Content-Length`` header, if any.

    When the server sends this header, tqdm can show ``55.0MB/55.0MB`` instead
    of an indeterminate bar. Returns ``None`` if the header is missing (still
    works; the bar just has no total).
    """
    raw = headers.get("content-length")
    if raw is None:
        return None
    try:
        length = int(raw)
    except (TypeError, ValueError):
        return None
    return length if length >= 0 else None


class ProgressBytesReader:
    """Pretend our in-memory ``bytes`` are a file that httpx can read chunk by chunk.

    httpx's upload API accepts either raw ``bytes`` (sent in one go) or an
    object with a ``.read(n)`` method (sent incrementally). This class implements
    ``.read(n)`` over ``data`` so we can update tqdm each time httpx pulls the
    next slice — similar to monitoring ``read()`` on a real checkpoint file.
    """

    def __init__(self, data: bytes, on_read: Callable[[int], None]) -> None:
        self._data = data
        self._pos = 0  # how many bytes we have already "read"
        self._on_read = on_read  # callback: advance the tqdm bar

    def read(self, size: int = -1) -> bytes:
        """Return up to ``size`` bytes and notify tqdm (called by httpx, not by you)."""
        if self._pos >= len(self._data):
            return b""
        if size < 0:
            chunk = self._data[self._pos :]
        else:
            chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        if chunk:
            self._on_read(len(chunk))
        return chunk

    def __len__(self) -> int:
        return len(self._data)


class ProgressFileReader:
    """Wrap a binary file object and update tqdm whenever httpx reads from it."""

    def __init__(self, file_obj: Any, on_read: Callable[[int], None]) -> None:
        """Store the wrapped stream and callback used for progress updates.

        Args:
            file_obj: Binary file-like object passed through to httpx.
            on_read: Callback invoked with the number of bytes read.

        Returns:
            None.
        """
        self._file_obj = file_obj
        self._on_read = on_read

    def read(self, size: int = -1) -> bytes:
        """Read bytes from the wrapped stream and update the progress callback.

        Args:
            size: Maximum number of bytes to read, or ``-1`` for all remaining
                bytes as expected by file-like objects.

        Returns:
            Bytes returned by the wrapped stream.
        """
        chunk = self._file_obj.read(size)
        if chunk:
            self._on_read(len(chunk))
        return chunk

    def seek(self, offset: int, whence: int = 0) -> int:
        """Move the wrapped stream position.

        Args:
            offset: Byte offset passed to the wrapped stream.
            whence: Seek mode using standard file-object constants.

        Returns:
            New stream position reported by the wrapped object.
        """
        return self._file_obj.seek(offset, whence)

    def tell(self) -> int:
        """Return the wrapped stream's current position.

        Args:
            None.

        Returns:
            Current byte offset reported by the wrapped object.
        """
        return self._file_obj.tell()


# Shape httpx expects for one file field in a multipart upload:
#   (filename shown to the server, body bytes or ProgressBytesReader, MIME type)
UploadMultipartBody = bytes | BinaryIO | ProgressBytesReader | ProgressFileReader
UploadMultipartFilePart = tuple[str, UploadMultipartBody, str]


def progress_file_reader(
    content: bytes,
    *,
    desc: str,
    total: int | None = None,
    disable: bool = False,
    position: int | None = None,
    leave: bool = True,
) -> tuple[ProgressBytesReader, TqdmBar]:
    """Wrap ``content`` for upload plus a tqdm bar; close the bar after the request."""
    tqdm = _get_tqdm()
    bar = tqdm(
        total=total if total is not None else len(content),
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=desc,
        disable=disable,
        position=position,
        leave=leave,
    )

    def on_read(num_bytes: int) -> None:
        """Advance the upload progress bar after a stream read.

        Args:
            num_bytes: Number of bytes just read from the wrapped stream.

        Returns:
            None.
        """
        bar.update(num_bytes)

    return ProgressBytesReader(content, on_read), bar


def progress_stream_reader(
    file_obj: Any,
    *,
    desc: str,
    total: int | None,
    disable: bool = False,
    position: int | None = None,
    leave: bool = True,
) -> tuple[ProgressFileReader, TqdmBar]:
    """Wrap a binary stream for upload progress without reading it into memory."""
    tqdm = _get_tqdm()
    bar = tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=desc,
        disable=disable,
        position=position,
        leave=leave,
    )

    def on_read(num_bytes: int) -> None:
        """Advance the upload progress bar after a stream read.

        Args:
            num_bytes: Number of bytes just read from the wrapped stream.

        Returns:
            None.
        """
        bar.update(num_bytes)

    return ProgressFileReader(file_obj, on_read), bar


def iter_download_chunks_with_progress(
    chunks: Iterator[bytes],
    *,
    desc: str,
    total: int | None,
    disable: bool = False,
    position: int | None = None,
    leave: bool = True,
) -> Iterator[bytes]:
    """Pass download chunks through unchanged while updating a tqdm bar."""
    tqdm = _get_tqdm()
    with tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=desc,
        disable=disable,
        position=position,
        leave=leave,
    ) as bar:
        for chunk in chunks:
            if chunk:
                bar.update(len(chunk))
            yield chunk


def batch_items_progress(
    *,
    total: int,
    desc: str,
    disable: bool,
) -> TqdmBar:
    """One tqdm bar that counts finished files in a batch transfer."""
    tqdm = _get_tqdm()
    return tqdm(total=total, unit="file", desc=desc, disable=disable)


# Tests import this older name.
_ProgressBytesReader = ProgressBytesReader
