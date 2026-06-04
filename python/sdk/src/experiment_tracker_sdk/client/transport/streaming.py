"""Streaming download helpers: open httpx stream, yield chunks, close connection."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import httpx

from experiment_tracker_sdk.client.request_types import FileDownloadResponse
from experiment_tracker_sdk.client.transport.errors import raise_for_status
from experiment_tracker_sdk.client.transport.headers import parse_content_disposition
from experiment_tracker_sdk.client.transport.options import RequestOptions
from experiment_tracker_sdk.client.utils.logging import disable_httpx_logging
from experiment_tracker_sdk.client.utils.transfer_progress import (
    UploadMultipartFilePart,
    content_length_from_headers,
    iter_download_chunks_with_progress,
)


def file_download_response_from_headers(
    response: httpx.Response,
    content: bytes | Iterator[bytes],
) -> FileDownloadResponse:
    """Wrap response bytes or chunks with filename and content-type metadata."""
    return FileDownloadResponse(
        content=content,
        filename=parse_content_disposition(response.headers.get("content-disposition")),
        content_type=response.headers.get("content-type", "application/octet-stream"),
    )


def open_streaming_download(
    client: httpx.Client,
    *,
    method: str,
    endpoint: str,
    suppress_errors: bool,
    json_payload: dict[str, Any] | None = None,
    form_data: dict[str, Any] | None = None,
    files: dict[str, UploadMultipartFilePart] | None = None,
    params: dict[str, Any] | None = None,
    options: RequestOptions,
) -> FileDownloadResponse:
    """Open a streaming request and return a managed file response.

    The HTTP connection stays open until the returned ``content`` iterator is
    fully consumed (or garbage-collected). The iterator's ``finally`` block
    exits the httpx stream context so connections are not leaked.

    When ``options.verbose`` is ``True``, chunks pass through tqdm before being
    yielded to the caller.
    """
    stream_context = client.stream(
        method,
        endpoint,
        json=json_payload,
        data=form_data,
        files=cast(Any, files),
        params=params,
    )
    with disable_httpx_logging():
        response = stream_context.__enter__()
    try:
        raise_for_status(response, suppress_errors)
    except Exception:  # noqa: BLE001
        # Fail fast: close connection if status is 4xx/5xx.
        stream_context.__exit__(None, None, None)
        raise

    total_bytes = content_length_from_headers(response.headers)
    progress_desc = options.progress_desc or "Download"

    def chunk_iterator() -> Iterator[bytes]:
        try:
            network_chunks = response.iter_bytes()
            if options.verbose:
                yield from iter_download_chunks_with_progress(
                    network_chunks,
                    desc=progress_desc,
                    total=total_bytes,
                    position=options.progress_position,
                    leave=options.progress_leave,
                )
            else:
                yield from network_chunks
        finally:
            stream_context.__exit__(None, None, None)

    return file_download_response_from_headers(response, chunk_iterator())
