from __future__ import annotations

from io import BytesIO
from typing import Any, Iterator, TypeVar, cast
from pathlib import Path

from experiment_tracker_sdk.client.utils.downloading import dump_binary_content_to_path

from .utils.logging import disable_httpx_logging

from .utils import log_error_response
import httpx

from .queue import RequestItem, RequestQueue
from .request_types import ApiRequestSpec, FileDownloadResponse, FileUploadSpec
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


def _build_httpx_files_from_request_spec(
    files: dict[str, FileUploadSpec] | None,
) -> dict[str, tuple[str, bytes, str]] | None:
    """Build a mapping of file names to tuples of (file_name, file_content, content_type) from a request spec.

    Args:
        files: Mapping of file names to FileUploadSpec objects.

    Returns:
        Mapping of file names to tuples of (file_name, file_content, content_type).
    """
    if files is None:
        return None
    # Mapping key: (file_name, file_content, content_type)
    return {
        key: (
            value.filename,
            value.content,
            value.content_type,
        )
        for key, value in files.items()
    }


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

    def _build_http_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
        }

    def request(
        self,
        request_spec: ApiRequestSpec[ResponseT],
        as_stream_download: bool | None = None,
    ) -> ResponseT | list[ResponseT] | dict[str, Any] | FileDownloadResponse:
        """Send a request and wait for the response.

        Args:
            request_spec: ApiRequestSpec describing request parameters.
            as_stream_download: If True, response body is returned as an
                iterator from ``httpx.Response.iter_bytes()`` wrapped in
                ``FileDownloadResponse``.
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

        # Build the files payload for the request.
        files_payload = _build_httpx_files_from_request_spec(request_spec.files)

        if stream_download:
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
                stream_context.__exit__(None, None, None)
                raise

            def _iter_response_bytes() -> Iterator[bytes]:
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

        # Send the request.
        with disable_httpx_logging():
            # For better readability
            if payload_is_json:
                # Send the request with the JSON payload.
                response = self._http_client.request(
                    request_spec.method,
                    request_spec.endpoint,
                    json=payload,
                    params=request_spec.query_params,
                )
            elif form_data_is_present:
                # Send the request with the form data (includes files).
                response = self._http_client.request(
                    request_spec.method,
                    request_spec.endpoint,
                    data=request_spec.form_data,
                    files=files_payload,
                    params=request_spec.query_params,
                )
            else:
                # Send the request with the files (no payload).
                response = self._http_client.request(
                    request_spec.method,
                    request_spec.endpoint,
                    files=files_payload,
                    params=request_spec.query_params,
                )
        _raise_for_status(response, self._supress_errors)

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

        # Parse the response body into a Pydantic model or list of models.
        # TODO: Add support for list of any.
        body = response.json()
        if request_spec.response_model is None:
            return body

        if issubclass(request_spec.response_model, RootModel):
            return request_spec.response_model.model_validate(body).root
        elif issubclass(request_spec.response_model, BaseModel):
            return request_spec.response_model.model_validate(body)
        else:
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

    def upload_file(
        self,
        endpoint: str,
        params: dict[str, Any],
        file_name: str,
        file_content: bytes,
        content_type: str = "application/octet-stream",
        form_data: dict[str, Any] | None = None,
        method: MethodT = "POST",
    ) -> dict[str, Any]:
        """Upload file to backend endpoint.

        Args:
            endpoint: The endpoint to upload the file to.
            params: The parameters to pass to the URI path of the endpoint.
            file_name: The name of the file to upload.
            file_content: The content of the file to upload.
            content_type: The content type of the file to upload (request still will use multipart/form-data for file upload).
            form_data: The form data to pass to the endpoint (backend will parse as Form data this params (not JSON)).
            method: The method to use to upload the file.
        """
        with disable_httpx_logging():
            # This request still uses multipart/form-data for file upload.
            response = self._http_client.request(
                method,
                endpoint,
                params=params,
                files={
                    "file": (
                        file_name,
                        file_content,
                        content_type,
                    )
                },
                data=form_data,
            )
        _raise_for_status(response, self._supress_errors)
        return response.json()

    def download_file(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        method: MethodT = "GET",
        as_stream_download: bool | None = None,
    ) -> FileDownloadResponse:
        """Download a file from backend endpoint, returning content and metadata.

        Args:
            endpoint: The endpoint to download the file from.
            params: Query parameters to pass to the endpoint.
            method: HTTP method to use.
            as_stream_download: If True, returns streamed bytes iterator in
                ``FileDownloadResponse.content``.
        """
        response: FileDownloadResponse = cast(
            FileDownloadResponse,
            self.request(
                ApiRequestSpec(
                    method=method,
                    endpoint=endpoint,
                    query_params=params,
                    response_model=FileDownloadResponse,
                ),
                as_stream_download=as_stream_download,
            ),
        )
        if not isinstance(response, FileDownloadResponse):
            raise TypeError("download_file expected FileDownloadResponse")
        return response

    def download_file_to_path(
        self,
        endpoint: str,
        output_path: str | Path,
        params: dict[str, Any] | None = None,
        method: MethodT = "GET",
        as_stream_download: bool | None = None,
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
        """
        download = self.download_file(
            endpoint=endpoint,
            params=params,
            method=method,
            as_stream_download=as_stream_download,
        )
        destination = dump_binary_content_to_path(
            download.content, output_path, download.filename
        )
        return destination

    def flush(self) -> None:
        """Flush the request queue."""
        self._queue.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        self._queue.close()
        self._http_client.close()
