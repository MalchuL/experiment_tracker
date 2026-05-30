"""Single HTTP send + response parse path for all synchronous SDK requests."""

from __future__ import annotations

from typing import Any, TypeVar, cast

import httpx
from pydantic import BaseModel, RootModel

from experiment_tracker_sdk.client.request_types import (
    ApiRequestSpec,
    FileDownloadResponse,
)
from experiment_tracker_sdk.client.transport.errors import (
    convert_payload_to_json,
    raise_for_status,
)
from experiment_tracker_sdk.client.transport.multipart import (
    build_multipart_files,
    close_progress_bars,
)
from experiment_tracker_sdk.client.transport.options import (
    RequestOptions,
    resolve_stream,
)
from experiment_tracker_sdk.client.transport.streaming import (
    file_download_response_from_headers,
    open_streaming_download,
)
from experiment_tracker_sdk.client.utils.logging import disable_httpx_logging

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class HttpRequestExecutor:
    """Perform one HTTP round-trip and parse the response.

    This is the only code path used by
    :meth:`~experiment_tracker_sdk.client.client.ExperimentTrackerClient.request`
    and by :class:`~experiment_tracker_sdk.client.file_transfer.FileTransferService`.

    Two response shapes:

    **Streaming download** — body is not loaded into RAM; caller receives a
    :class:`~experiment_tracker_sdk.client.request_types.FileDownloadResponse`
    whose ``content`` is a chunk iterator. Used when the spec marks a download
    and :func:`~experiment_tracker_sdk.client.transport.options.resolve_stream`
    returns ``True``.

    **Buffered request** — full response received, then either JSON (Pydantic
    model / dict), or a :class:`FileDownloadResponse` when the server sends
    ``Content-Disposition``.
    """

    def __init__(self, *, suppress_errors: bool = False) -> None:
        self._suppress_errors = suppress_errors

    def execute(
        self,
        http_client: httpx.Client,
        spec: ApiRequestSpec[ResponseT],
        options: RequestOptions | None = None,
    ) -> ResponseT | dict[str, Any] | FileDownloadResponse:
        """Send ``spec`` via ``http_client`` and return the parsed result.

        Args:
            http_client: Live httpx client (passed per call so tests can swap it).
            spec: Method, path, body, and expected response type.
            options: Progress bars and streaming; defaults to no tqdm, buffered I/O.
        """
        opts = options or RequestOptions()
        # Convert REQUEST Pydantic models to JSON dicts for httpx or to None.
        payload = convert_payload_to_json(spec.request_payload)
        payload_is_json = payload is not None
        # Check if form data in REQUEST is present.
        form_data_is_present = spec.form_data is not None

        # Check if the RESPONSE is a download (stream or FileDownloadResponse).
        is_download = self._is_download(spec, opts)

        # Upload progress only; verbose on a download must not wrap upload parts.
        files_payload, upload_bars = build_multipart_files(
            spec.files,
            verbose=opts.verbose and not is_download,
            progress_position=opts.progress_position,
            progress_leave=opts.progress_leave,
        )
        try:
            if is_download and resolve_stream(opts, is_download=True):
                return open_streaming_download(
                    http_client,
                    method=spec.method,
                    endpoint=spec.endpoint,
                    suppress_errors=self._suppress_errors,
                    json_payload=payload if payload_is_json else None,
                    form_data=spec.form_data if form_data_is_present else None,
                    files=files_payload,
                    params=spec.query_params,
                    options=opts,
                )
            response = self._buffered_request(
                http_client=http_client,
                spec=spec,
                payload=payload,
                payload_is_json=payload_is_json,
                form_data_is_present=form_data_is_present,
                files_payload=files_payload,
            )
            return self._parse_response(response, spec)
        finally:
            close_progress_bars(upload_bars)

    def _is_download(self, spec: ApiRequestSpec[Any], options: RequestOptions) -> bool:
        """Whether this spec expects a file body rather than JSON."""
        if spec.response_model is FileDownloadResponse:
            return True
        if options.stream is True:
            return True
        return False

    def _buffered_request(
        self,
        *,
        http_client: httpx.Client,
        spec: ApiRequestSpec[ResponseT],
        payload: dict[str, Any] | None,
        payload_is_json: bool,
        form_data_is_present: bool,
        files_payload: dict | None,
    ) -> httpx.Response:
        """Perform a blocking httpx request; entire response body is buffered."""
        with disable_httpx_logging():
            # httpx allows only one body style per request; the spec guarantees which is set.
            if payload_is_json:
                return http_client.request(
                    spec.method,
                    spec.endpoint,
                    json=payload,
                    params=spec.query_params,
                )
            if form_data_is_present:
                return http_client.request(
                    spec.method,
                    spec.endpoint,
                    data=spec.form_data,
                    files=files_payload,
                    params=spec.query_params,
                )
            return http_client.request(
                spec.method,
                spec.endpoint,
                files=files_payload,
                params=spec.query_params,
            )

    def _parse_response(
        self,
        response: httpx.Response,
        spec: ApiRequestSpec[ResponseT],
    ) -> ResponseT | dict[str, Any] | FileDownloadResponse:
        """Map a buffered httpx response to a model, dict, or file wrapper."""
        raise_for_status(response, self._suppress_errors)

        if response.headers.get("content-disposition"):
            return file_download_response_from_headers(response, response.content)

        body = response.json()
        if spec.response_model is None:
            return body

        if spec.response_model is FileDownloadResponse:
            return file_download_response_from_headers(response, response.content)

        if issubclass(spec.response_model, RootModel):
            return cast(
                ResponseT,
                spec.response_model.model_validate(body).root,
            )
        if issubclass(spec.response_model, BaseModel):
            return cast(ResponseT, spec.response_model.model_validate(body))
        return body
