from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO
from typing import Any, Iterator, TypeVar, cast
from pathlib import Path

from experiment_tracker_sdk.client.utils.downloading import dump_binary_content_to_path
from experiment_tracker_sdk.client.utils.transfer_progress import (
    UploadMultipartBody,
    UploadMultipartFilePart,
    batch_items_progress,
    content_length_from_headers,
    iter_download_chunks_with_progress,
    progress_file_reader,
)

from .utils.logging import disable_httpx_logging

from .utils import log_error_response
import httpx

from .queue import RequestItem, RequestQueue
from .request_types import (
    ApiRequestSpec,
    FileDownloadItem,
    FileDownloadResponse,
    FileDownloadToPathItem,
    FileUploadItem,
    FileUploadSpec,
)
from ..config import compose_base_url, normalize_api_prefix
from ..logger import logger
from pydantic import BaseModel, RootModel
from .request_types import MethodT

ResponseT = TypeVar("ResponseT", bound=BaseModel)


def _raise_for_status(response: httpx.Response, supress_errors: bool) -> None:
    try:
        response.raise_for_status()
    except Exception:  # noqa: BLE001
        log_error_response(response, logger)
        if not supress_errors:
            raise


def _convert_payload_to_json(
    payload: dict[str, Any] | BaseModel | None,
) -> dict[str, Any] | None:
    """Convert a payload to a JSON dictionary.

    Args:
        payload: Payload to convert to a JSON dictionary.

    Returns:
        JSON dictionary or None if the payload is None.
    """
    if isinstance(payload, BaseModel):
        return payload.model_dump(exclude_unset=True)
    return payload  # None or dict[str, Any]


def _parse_content_disposition_filename(header: str | None) -> str | None:
    """Extract filename from a Content-Disposition header value.

    Handles both plain ``filename="foo.png"`` and the RFC 5987
    ``filename*=UTF-8''foo%20bar.png`` encoding that the backend uses.
    """
    if not header:
        return None
    import re
    from urllib.parse import unquote

    # RFC 5987: filename*=UTF-8''<percent-encoded>  (preferred, checked first)
    m = re.search(r"filename\*\s*=\s*[^']*''(.+?)(?:;|$)", header, re.IGNORECASE)
    if m:
        return unquote(m.group(1).strip())
    # Plain: filename="foo.png" or filename=foo.png
    m = re.search(r'filename\s*=\s*"?([^";]+)"?', header, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _close_tqdm_bars(bars: list[Any]) -> None:
    """Release tqdm UI resources after an upload request finishes."""
    for bar in bars:
        bar.close()


def _streaming_download_enabled(
    as_stream_download: bool | None, *, verbose: bool
) -> bool:
    """Whether to read the HTTP response body chunk-by-chunk instead of all at once.

    Streaming uses less RAM for large artifacts (e.g. a 2 GB checkpoint). Verbose
    mode always streams so tqdm can tick forward as each chunk arrives.
    """
    if verbose:
        return True
    return bool(as_stream_download)


def _build_httpx_files_from_request_spec(
    files: dict[str, FileUploadSpec] | None,
    *,
    verbose: bool = False,
) -> tuple[dict[str, UploadMultipartFilePart] | None, list[Any]]:
    """Convert SDK file specs into the tuple shape httpx expects for multipart uploads.

    Returns ``(httpx_files, progress_bars)``. Caller must close ``progress_bars``
    after the HTTP request completes (see :func:`_close_tqdm_bars`).
    """
    if files is None:
        return None, []

    httpx_files: dict[str, UploadMultipartFilePart] = {}
    progress_bars: list[Any] = []

    for field_name, spec in files.items():
        # Default: send the whole byte buffer at once (no progress bar).
        body: UploadMultipartBody = spec.content
        if verbose:
            # Wrap bytes so httpx calls .read() in slices and tqdm can update.
            body, bar = progress_file_reader(
                spec.content, desc=f"Upload {spec.filename}"
            )
            progress_bars.append(bar)
        httpx_files[field_name] = (spec.filename, body, spec.content_type)

    return httpx_files, progress_bars


class ExperimentTrackerClient:
    def __init__(
        self,
        base_url: str,
        api_token: str,
        api_prefix: str = "/api",
        timeout: float = 30.0,
        max_queue_size: int = 1000,
        supress_errors: bool = False,
    ):
        """Initialize a synchronous SDK client for Experiment Tracker.

        Args:
            base_url: Backend base URL, e.g. "http://127.0.0.1:8000".
            api_token: API token used for Authorization header.
            api_prefix: Optional API path prefix, e.g. "/api".
            timeout: HTTP timeout (seconds) for requests.
            max_queue_size: Max queued metric requests before blocking.

        Example:
            client = ExperimentTrackerClient(
                base_url="http://127.0.0.1:8000",
                api_token="my-token",
            )
        """
        self.base_url = compose_base_url(base_url, api_prefix)
        self.api_prefix = normalize_api_prefix(api_prefix)
        self.api_token = api_token
        self._http_client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._build_http_headers(),
        )
        self._queue = RequestQueue(self._http_client, max_queue_size=max_queue_size)
        self._supress_errors = supress_errors

    @property
    def is_closed(self) -> bool:
        """Return whether the underlying HTTP client has been closed."""
        return self._http_client.is_closed

    def probe_http_status(self, method: MethodT, endpoint: str) -> int:
        """Perform a simple request and return the HTTP status (body discarded)."""
        with disable_httpx_logging():
            response = self._http_client.request(method, endpoint)
        _raise_for_status(response, self._supress_errors)
        return response.status_code

    def _build_http_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
        }

    def request(
        self,
        request_spec: ApiRequestSpec[ResponseT],
        as_stream_download: bool | None = None,
        verbose: bool = False,
    ) -> ResponseT | list[ResponseT] | dict[str, Any] | FileDownloadResponse:
        """Send a request and wait for the response.

        Args:
            request_spec: ApiRequestSpec describing request parameters.
            as_stream_download: If True, response body is returned as an
                iterator from ``httpx.Response.iter_bytes()`` wrapped in
                ``FileDownloadResponse``.
            verbose: When ``True`` and the spec includes file uploads, show a
                tqdm byte progress bar while each file part is sent.
        """
        stream_download = bool(as_stream_download)
        payload = _convert_payload_to_json(request_spec.request_payload)

        # Check that the request spec is valid.
        payload_is_json = payload is not None
        form_data_is_present = request_spec.form_data is not None
        files_is_present = request_spec.files is not None
        payload_is_form = form_data_is_present or files_is_present

        if payload_is_json and payload_is_form:
            raise ValueError(
                "ApiRequestSpec cannot contain both request_payload (json) and form_data/files (multipart/form-data)"
            )

        files_payload, upload_progress_bars = _build_httpx_files_from_request_spec(
            request_spec.files, verbose=verbose
        )
        try:
            return self._send_request(
                request_spec=request_spec,
                payload=payload,
                payload_is_json=payload_is_json,
                form_data_is_present=form_data_is_present,
                files_payload=files_payload,
                stream_download=stream_download,
            )
        finally:
            _close_tqdm_bars(upload_progress_bars)

    def _send_request(
        self,
        *,
        request_spec: ApiRequestSpec[ResponseT],
        payload: dict[str, Any] | None,
        payload_is_json: bool,
        form_data_is_present: bool,
        files_payload: dict[str, UploadMultipartFilePart] | None,
        stream_download: bool,
    ) -> ResponseT | list[ResponseT] | dict[str, Any] | FileDownloadResponse:
        """Perform the HTTP call after :meth:`request` has validated the spec.

        This is the low-level send step. :meth:`request` prepares arguments (JSON
        vs multipart, optional upload progress bars) and calls here.

        Two completely different response shapes:

        **A) ``stream_download=True``** (large file downloads, verbose bars)
            Opens a streaming connection. The body is *not* loaded into RAM yet;
            the caller receives a :class:`~experiment_tracker_sdk.client.request_types.FileDownloadResponse`
            whose ``content`` is an iterator of byte chunks. The connection stays
            open until that iterator is exhausted (see ``_iter_response_bytes``).

        **B) ``stream_download=False``** (typical API calls)
            Waits for the full response, then either:
            - returns a :class:`~experiment_tracker_sdk.client.request_types.FileDownloadResponse`
              if the server sent a ``Content-Disposition`` header (small file
              download buffered in memory), or
            - parses JSON and validates with ``request_spec.response_model``.

        Args:
            request_spec: Method, path, query params, and expected response type.
            payload: JSON body dict, or ``None`` when using form/multipart instead.
            payload_is_json: If ``True``, send ``payload`` as ``application/json``.
            form_data_is_present: If ``True``, send HTML form fields (often together
                with ``files_payload`` for artifact uploads).
            files_payload: Multipart file parts for httpx, or ``None``.
            stream_download: Chooses path A vs B above.

        Returns:
            Parsed model, raw JSON dict, or :class:`~experiment_tracker_sdk.client.request_types.FileDownloadResponse`.
        """
        # --- Path A: streaming download (chunk iterator, not full body in RAM) ---
        if stream_download:
            # ``stream()`` is a context manager: connection must be closed when done.
            stream_context = self._http_client.stream(
                request_spec.method,
                request_spec.endpoint,
                json=payload if payload_is_json else None,
                data=request_spec.form_data if form_data_is_present else None,
                files=files_payload,
                params=request_spec.query_params,
            )
            with disable_httpx_logging():
                response = stream_context.__enter__()
            try:
                _raise_for_status(response, self._supress_errors)
            except Exception:  # noqa: BLE001
                # Fail fast: close connection if status is 4xx/5xx.
                stream_context.__exit__(None, None, None)
                raise

            def _iter_response_bytes() -> Iterator[bytes]:
                # Consumer reads this generator (e.g. writing to disk). When it
                # finishes—or on error—we must exit the stream context.
                try:
                    yield from response.iter_bytes()
                finally:
                    stream_context.__exit__(None, None, None)

            return FileDownloadResponse(
                content=_iter_response_bytes(),
                filename=_parse_content_disposition_filename(
                    response.headers.get("content-disposition")
                ),
                content_type=response.headers.get(
                    "content-type", "application/octet-stream"
                ),
            )

        # --- Path B: normal request (entire response received before return) ---
        with disable_httpx_logging():
            # httpx allows only one body style per request; spec guarantees
            # which one is set (see validation in :meth:`request`).
            if payload_is_json:
                response = self._http_client.request(
                    request_spec.method,
                    request_spec.endpoint,
                    json=payload,
                    params=request_spec.query_params,
                )
            elif form_data_is_present:
                # Typical artifact upload: form fields + file part(s).
                response = self._http_client.request(
                    request_spec.method,
                    request_spec.endpoint,
                    data=request_spec.form_data,
                    files=files_payload,
                    params=request_spec.query_params,
                )
            else:
                # Rare: files only, no separate form fields.
                response = self._http_client.request(
                    request_spec.method,
                    request_spec.endpoint,
                    files=files_payload,
                    params=request_spec.query_params,
                )
        _raise_for_status(response, self._supress_errors)

        # Server returned a file attachment (buffered whole body in memory).
        # TODO: Handle binary response like stream response.
        if response.headers.get("content-disposition"):
            return FileDownloadResponse(
                content=response.content,
                filename=_parse_content_disposition_filename(
                    response.headers.get("content-disposition")
                ),
                content_type=response.headers.get(
                    "content-type", "application/octet-stream"
                ),
            )

        # Default: JSON API response → dict or Pydantic model.
        # TODO: Add support for list of any.
        body = response.json()
        if request_spec.response_model is None:
            return body

        if issubclass(request_spec.response_model, RootModel):
            return cast(
                ResponseT,
                request_spec.response_model.model_validate(body).root,
            )
        if issubclass(request_spec.response_model, BaseModel):
            return cast(ResponseT, request_spec.response_model.model_validate(body))
        return body

    def queued_request(
        self,
        request_spec: ApiRequestSpec[Any],
        as_stream_download: bool | None = None,
    ) -> None:
        """Enqueue a request to be sent in the background.

        Args:
            request_spec: ApiRequestSpec describing request parameters.
            as_stream_download: Reserved for parity with ``request`` API.
                ``queued_request`` cannot stream-download responses.
        """
        if as_stream_download:
            raise ValueError("queued_request does not support as_stream_download=True")
        payload = _convert_payload_to_json(request_spec.request_payload)
        if payload is not None and (
            request_spec.form_data is not None or request_spec.files is not None
        ):
            raise ValueError(
                "ApiRequestSpec cannot contain both request_payload (json) and form_data/files (multipart/form-data)"
            )
        self._queue.enqueue(
            RequestItem(
                method=request_spec.method,
                path=request_spec.endpoint,
                json=payload,
                form_data=request_spec.form_data,
                files=request_spec.files,
                params=request_spec.query_params,
            )
        )

    # -------------------------------------------------------------------------
    # File upload / download (multipart HTTP and optional tqdm progress)
    # -------------------------------------------------------------------------

    def _upload_file_multipart(
        self,
        *,
        method: MethodT,
        endpoint: str,
        params: dict[str, Any],
        file_payload: UploadMultipartFilePart,
        form_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """POST (or PUT) one file using HTML multipart encoding — same as a browser file input."""
        with disable_httpx_logging():
            response = self._http_client.request(
                method,
                endpoint,
                params=params,
                files={"file": file_payload},
                data=form_data,
            )
        _raise_for_status(response, self._supress_errors)
        return response.json()

    def upload_file(
        self,
        endpoint: str,
        params: dict[str, Any],
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        form_data: dict[str, Any] | None = None,
        method: MethodT = "POST",
        verbose: bool = False,
        progress_position: int | None = None,
        progress_leave: bool = True,
    ) -> dict[str, Any]:
        """Upload one file to a backend endpoint via multipart form data.

        Sends a single ``file`` part plus optional form fields. When
        ``verbose`` is enabled, the request body is streamed through a
        file-like reader so tqdm can report byte-level upload progress.

        Args:
            endpoint: Path relative to the client base URL (for example
                ``/api/project-artifacts/{project_id}/upload``).
            params: Query parameters appended to the request URL (for example
                ``{"hash": "<sha256>"}``).
            filename: Filename sent in the multipart ``Content-Disposition``
                header for the ``file`` part.
            content: Raw file bytes to upload.
            content_type: MIME type of the ``file`` part. The request still
                uses ``multipart/form-data`` encoding.
            form_data: Optional extra form fields parsed by the backend as
                HTML form data (not JSON).
            method: HTTP method to use (default ``POST``).
            verbose: When ``True``, display a tqdm byte progress bar while
                the file is uploaded.
            progress_position: Optional tqdm ``position`` for nested bars (used
                by :meth:`upload_files_batch` to stack a per-file bar under a
                batch counter). Ignored when ``verbose`` is ``False``.
            progress_leave: Whether the per-file tqdm bar remains on screen
                after completion. Batch uploads pass ``False`` so only the
                outer batch bar persists.

        Returns:
            Parsed JSON response body from the server.
        """
        body: UploadMultipartBody = content
        progress_bar = None
        if verbose:
            body, progress_bar = progress_file_reader(
                content,
                desc=f"Upload {filename}",
                position=progress_position,
                leave=progress_leave,
            )
        file_payload: UploadMultipartFilePart = (filename, body, content_type)
        try:
            return self._upload_file_multipart(
                method=method,
                endpoint=endpoint,
                params=params,
                file_payload=file_payload,
                form_data=form_data,
            )
        finally:
            if progress_bar is not None:
                progress_bar.close()

    def upload_files_batch(
        self,
        endpoint: str,
        items: Sequence[FileUploadItem],
        method: MethodT = "POST",
        verbose: bool = False,
    ) -> list[dict[str, Any]]:
        """Upload many files through one endpoint, varying query params per item.

        Each :class:`~experiment_tracker_sdk.client.request_types.FileUploadItem`
        is uploaded with the same ``endpoint`` and ``method`` as
        :meth:`upload_file`, but may supply different ``params``, filenames,
        bytes, form fields, and optional ``label`` values for progress display.

        When ``verbose`` is ``True``, a batch-level tqdm counter tracks completed
        files and each item shows its own byte-level upload bar underneath.

        Args:
            endpoint: Shared path relative to the client base URL.
            items: Ordered list of per-file upload specifications.
            method: HTTP method applied to every item (default ``POST``).
            verbose: When ``True``, show batch and per-file tqdm progress bars.

        Returns:
            List of parsed JSON response bodies, one per item in the same order
            as ``items``.
        """
        results: list[dict[str, Any]] = []
        # Outer bar: "file 2/5". Inner bar (per upload_file): bytes for that file.
        batch_bar = (
            batch_items_progress(total=len(items), desc="Upload batch", disable=False)
            if verbose and items
            else None
        )
        try:
            for item in items:
                if batch_bar is not None:
                    batch_bar.set_postfix_str(item.label or item.filename)
                results.append(
                    self.upload_file(
                        endpoint=endpoint,
                        params=item.params,
                        filename=item.filename,
                        content=item.content,
                        content_type=item.content_type,
                        form_data=item.form_data,
                        method=method,
                        verbose=verbose,
                        progress_position=1 if verbose else None,
                        progress_leave=False,
                    )
                )
                if batch_bar is not None:
                    batch_bar.update(1)
        finally:
            if batch_bar is not None:
                batch_bar.close()
        return results

    def _download_file_response(
        self,
        *,
        endpoint: str,
        params: dict[str, Any] | None,
        method: MethodT,
        as_stream_download: bool,
        verbose: bool,
        progress_desc: str,
        progress_position: int | None = None,
        progress_leave: bool = True,
    ) -> FileDownloadResponse:
        """Fetch one file from the API and wrap bytes + filename metadata.

        Small file, no progress bar: load entire body into RAM (``bytes``).
        Large file and/or ``verbose``: return an *iterator* of chunks; consumer
        (e.g. ``download_file_to_path``) writes each chunk to disk without
        holding the full file in memory.
        """
        use_streaming = as_stream_download or verbose

        # --- Simple path: one blocking request, full body in memory ---
        if not use_streaming:
            response: FileDownloadResponse = cast(
                FileDownloadResponse,
                self.request(
                    ApiRequestSpec(
                        method=method,
                        endpoint=endpoint,
                        query_params=params,
                        response_model=FileDownloadResponse,
                    ),
                    as_stream_download=False,
                ),
            )
            if not isinstance(response, FileDownloadResponse):
                raise TypeError("download_file expected FileDownloadResponse")
            return response

        # --- Streaming path: open connection, read chunks as they arrive ---
        stream_context = self._http_client.stream(method, endpoint, params=params)
        with disable_httpx_logging():
            http_response = stream_context.__enter__()
        try:
            _raise_for_status(http_response, self._supress_errors)
        except Exception:  # noqa: BLE001
            stream_context.__exit__(None, None, None)
            raise

        total_bytes = content_length_from_headers(http_response.headers)

        def chunk_iterator() -> Iterator[bytes]:
            """Yield network chunks; close the HTTP connection when done."""
            try:
                network_chunks = http_response.iter_bytes()
                if verbose:
                    yield from iter_download_chunks_with_progress(
                        network_chunks,
                        desc=progress_desc,
                        total=total_bytes,
                        position=progress_position,
                        leave=progress_leave,
                    )
                else:
                    yield from network_chunks
            finally:
                stream_context.__exit__(None, None, None)

        return FileDownloadResponse(
            content=chunk_iterator(),
            filename=_parse_content_disposition_filename(
                http_response.headers.get("content-disposition")
            ),
            content_type=http_response.headers.get(
                "content-type", "application/octet-stream"
            ),
        )

    def download_file(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        method: MethodT = "GET",
        as_stream_download: bool | None = None,
        verbose: bool = False,
    ) -> FileDownloadResponse:
        """Download a file from backend endpoint, returning content and metadata.

        Args:
            endpoint: The endpoint to download the file from.
            params: Query parameters to pass to the endpoint.
            method: HTTP method to use.
            as_stream_download: If True, returns streamed bytes iterator in
                ``FileDownloadResponse.content``. Defaults to True when
                ``verbose`` is True.
            verbose: If True, show a tqdm byte progress bar while downloading.

        Returns:
            :class:`~experiment_tracker_sdk.client.request_types.FileDownloadResponse`
            with file bytes (or a streaming iterator when
            ``as_stream_download`` or ``verbose`` is enabled), plus response
            metadata.
        """
        use_streaming = _streaming_download_enabled(as_stream_download, verbose=verbose)
        name = params.get("name") if params else None
        progress_desc = (
            f"Download {name}"
            if isinstance(name, str)
            else f"Download {endpoint.rsplit('/', 1)[-1]}"
        )
        return self._download_file_response(
            endpoint=endpoint,
            params=params,
            method=method,
            as_stream_download=use_streaming,
            verbose=verbose,
            progress_desc=progress_desc,
        )

    def download_files_batch(
        self,
        endpoint: str,
        items: Sequence[FileDownloadItem],
        method: MethodT = "GET",
        as_stream_download: bool | None = None,
        verbose: bool = False,
    ) -> list[FileDownloadResponse]:
        """Download many files from one endpoint with per-item query parameters.

        Each :class:`~experiment_tracker_sdk.client.request_types.FileDownloadItem`
        is fetched with the same ``endpoint`` and ``method`` as
        :meth:`download_file`, but may supply different ``params`` and an
        optional ``label`` for progress display.

        When ``verbose`` is ``True``, a batch-level tqdm counter tracks completed
        files and each item shows its own byte-level download bar underneath.
        When ``verbose`` is ``True`` and ``as_stream_download`` is omitted,
        streaming is enabled automatically for every item.

        Args:
            endpoint: Shared path relative to the client base URL.
            items: Ordered list of per-file download specifications.
            method: HTTP method applied to every item (default ``GET``).
            as_stream_download: When ``True``, each result's ``content`` is a
                bytes iterator. Defaults to ``True`` when ``verbose`` is
                ``True``; otherwise defaults to ``False``.
            verbose: When ``True``, show batch and per-file tqdm progress bars.

        Returns:
            List of download responses, one per item in the same order as
            ``items``. Each entry is a
            :class:`~experiment_tracker_sdk.client.request_types.FileDownloadResponse`.
        """
        use_streaming = _streaming_download_enabled(as_stream_download, verbose=verbose)
        results: list[FileDownloadResponse] = []
        batch_bar = (
            batch_items_progress(total=len(items), desc="Download batch", disable=False)
            if verbose and items
            else None
        )
        try:
            for index, item in enumerate(items):
                if batch_bar is not None:
                    batch_bar.set_postfix_str(item.label or str(index + 1))
                label = item.label or (item.params.get("name") if item.params else None)
                progress_desc = (
                    f"Download {label}"
                    if isinstance(label, str)
                    else f"Download {index + 1}/{len(items)}"
                )
                results.append(
                    self._download_file_response(
                        endpoint=endpoint,
                        params=item.params,
                        method=method,
                        as_stream_download=use_streaming,
                        verbose=verbose,
                        progress_desc=progress_desc,
                        progress_position=1 if verbose else None,
                        progress_leave=False,
                    )
                )
                if batch_bar is not None:
                    batch_bar.update(1)
        finally:
            if batch_bar is not None:
                batch_bar.close()
        return results

    def download_file_to_path(
        self,
        endpoint: str,
        output_path: str | Path,
        params: dict[str, Any] | None = None,
        method: MethodT = "GET",
        as_stream_download: bool | None = None,
        verbose: bool = False,
    ) -> Path:
        """Download a file and persist it to the local filesystem.

        If ``output_path`` is a directory, the filename from the
        Content-Disposition header is used; falls back to the last path segment
        of the endpoint.

        Args:
            endpoint: The endpoint to download the file from.
            output_path: Destination file path or directory.
            params: Query parameters to pass to the endpoint.
            method: HTTP method to use.
            as_stream_download: If True, writes streamed bytes chunks to disk.
                Defaults to True when ``verbose`` is True.
            verbose: If True, show a tqdm byte progress bar while downloading.

        Returns:
            Resolved filesystem path where the file was written. If
            ``output_path`` is a directory, the filename comes from the
            ``Content-Disposition`` header when available.
        """
        download = self.download_file(
            endpoint=endpoint,
            params=params,
            method=method,
            as_stream_download=_streaming_download_enabled(
                as_stream_download, verbose=verbose
            ),
            verbose=verbose,
        )
        destination = dump_binary_content_to_path(
            download.content, output_path, download.filename
        )
        return destination

    def download_files_batch_to_paths(
        self,
        endpoint: str,
        items: Sequence[FileDownloadToPathItem],
        method: MethodT = "GET",
        as_stream_download: bool | None = None,
        verbose: bool = False,
    ) -> list[Path]:
        """Download many files and write each one to a local path.

        Combines :meth:`download_file` streaming semantics with
        :meth:`download_file_to_path` persistence. Each
        :class:`~experiment_tracker_sdk.client.request_types.FileDownloadToPathItem`
        uses the same ``endpoint`` and ``method`` but may differ in ``params``,
        ``output_path``, and optional ``label``.

        If an ``output_path`` is a directory, the filename from the response
        ``Content-Disposition`` header is appended (same rules as
        :meth:`download_file_to_path`).

        When ``verbose`` is ``True``, a batch-level tqdm counter tracks completed
        files and each item shows its own byte-level download bar underneath.
        When ``verbose`` is ``True`` and ``as_stream_download`` is omitted,
        streaming is enabled automatically for every item.

        Args:
            endpoint: Shared path relative to the client base URL.
            items: Ordered list of per-file download targets.
            method: HTTP method applied to every item (default ``GET``).
            as_stream_download: When ``True``, stream bytes to disk chunk by
                chunk. Defaults to ``True`` when ``verbose`` is ``True``;
                otherwise defaults to ``False``.
            verbose: When ``True``, show batch and per-file tqdm progress bars.

        Returns:
            List of resolved filesystem paths where each file was written, in
            the same order as ``items``.
        """
        use_streaming = _streaming_download_enabled(as_stream_download, verbose=verbose)
        paths: list[Path] = []
        batch_bar = (
            batch_items_progress(total=len(items), desc="Download batch", disable=False)
            if verbose and items
            else None
        )
        try:
            for item in items:
                if batch_bar is not None:
                    batch_bar.set_postfix_str(item.label or Path(item.output_path).name)
                download = self._download_file_response(
                    endpoint=endpoint,
                    params=item.params,
                    method=method,
                    as_stream_download=use_streaming,
                    verbose=verbose,
                    progress_desc=item.label or Path(item.output_path).name,
                    progress_position=1 if verbose else None,
                    progress_leave=False,
                )
                # download.content is either bytes or a chunk iterator; helper writes disk.
                paths.append(
                    dump_binary_content_to_path(
                        download.content, item.output_path, download.filename
                    )
                )
                if batch_bar is not None:
                    batch_bar.update(1)
        finally:
            if batch_bar is not None:
                batch_bar.close()
        return paths

    def flush(self) -> None:
        """Flush the request queue."""
        self._queue.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        try:
            self._queue.close()
        except Exception:
            pass
        if not self.is_closed:
            try:
                self._http_client.close()
            except Exception:
                pass
