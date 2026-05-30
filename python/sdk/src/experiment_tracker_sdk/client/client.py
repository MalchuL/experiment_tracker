from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeVar

import httpx

from experiment_tracker_sdk.client.file_transfer import FileTransferService
from experiment_tracker_sdk.client.queue import RequestItem, RequestQueue
from experiment_tracker_sdk.client.request_types import (
    ApiRequestSpec,
    FileDownloadItem,
    FileDownloadResponse,
    FileDownloadToPathItem,
    FileUploadItem,
)
from experiment_tracker_sdk.client.transport.errors import (
    convert_payload_to_json,
    raise_for_status,
)
from experiment_tracker_sdk.client.transport.executor import HttpRequestExecutor
from experiment_tracker_sdk.client.transport.options import RequestOptions
from experiment_tracker_sdk.client.utils.logging import disable_httpx_logging
from experiment_tracker_sdk.config import compose_base_url, normalize_api_prefix
from pydantic import BaseModel

from .request_types import MethodT

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class ExperimentTrackerClient:
    """Synchronous HTTP client for the Experiment Tracker backend.

    JSON API calls use :meth:`request`. Artifact uploads/downloads typically go
    through :class:`~experiment_tracker_sdk.client.artifact_client.ArtifactClient`.
    Scalar logging during training may use :meth:`queued_request` for fire-and-forget
    batches. Multi-file I/O against a shared endpoint uses the ``*_files_batch*``
    helpers (see :mod:`~experiment_tracker_sdk.client.file_transfer`).
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        api_prefix: str = "/api",
        timeout: float = 30.0,
        max_queue_size: int = 1000,
        supress_errors: bool = False,
    ):
        """Initialize the client.

        Args:
            base_url: Backend origin, e.g. ``http://127.0.0.1:8000``.
            api_token: Bearer token for the ``Authorization`` header.
            api_prefix: API path prefix (default ``/api``).
            timeout: httpx timeout in seconds.
            max_queue_size: Max queued background requests before blocking.
            supress_errors: When ``True``, log HTTP errors without raising.
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
        self._executor = HttpRequestExecutor(suppress_errors=supress_errors)
        self._file_transfer = FileTransferService(self._executor)

    @property
    def is_closed(self) -> bool:
        """Return whether the underlying httpx client has been closed."""
        return self._http_client.is_closed

    def probe_http_status(self, method: MethodT, endpoint: str) -> int:
        """Perform a simple request and return the HTTP status (body discarded)."""
        with disable_httpx_logging():
            response = self._http_client.request(method, endpoint)
        raise_for_status(response, self._supress_errors)
        return response.status_code

    def _build_http_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_token}"}

    def request(
        self,
        request_spec: ApiRequestSpec[ResponseT],
        *,
        options: RequestOptions | None = None,
    ) -> ResponseT | dict[str, Any] | FileDownloadResponse:
        """Send a request and wait for the response.

        Args:
            request_spec: Built by a domain spec factory (``registry.*``).
            options: Optional tqdm progress and streaming download behavior.
                See :class:`~experiment_tracker_sdk.client.transport.options.RequestOptions`.

        Returns:
            Parsed Pydantic model, raw JSON ``dict``, or
            :class:`~experiment_tracker_sdk.client.request_types.FileDownloadResponse`.
        """
        return self._executor.execute(self._http_client, request_spec, options)

    def queued_request(self, request_spec: ApiRequestSpec[Any]) -> None:
        """Enqueue a request for the background worker (scalars, etc.).

        Does not support streaming downloads. Call :meth:`flush` to wait for
        queued items to finish.
        """
        payload = convert_payload_to_json(request_spec.request_payload)
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

    def upload_files_batch(
        self,
        endpoint: str,
        items: Sequence[FileUploadItem],
        method: MethodT = "POST",
        *,
        options: RequestOptions | None = None,
    ) -> list[dict[str, Any]]:
        """Upload many files through one endpoint; see :class:`FileTransferService`."""
        return self._file_transfer.upload_files_batch(
            self._http_client, endpoint, items, method, options=options
        )

    def download_files_batch(
        self,
        endpoint: str,
        items: Sequence[FileDownloadItem],
        method: MethodT = "GET",
        *,
        options: RequestOptions | None = None,
    ) -> list[FileDownloadResponse]:
        """Download many files from one endpoint; see :class:`FileTransferService`."""
        return self._file_transfer.download_files_batch(
            self._http_client, endpoint, items, method, options=options
        )

    def download_files_batch_to_paths(
        self,
        endpoint: str,
        items: Sequence[FileDownloadToPathItem],
        method: MethodT = "GET",
        *,
        options: RequestOptions | None = None,
    ) -> list[Path]:
        """Download many files and write each to disk; see :class:`FileTransferService`."""
        return self._file_transfer.download_files_batch_to_paths(
            self._http_client, endpoint, items, method, options=options
        )

    def flush(self) -> None:
        """Wait until all queued requests have been sent."""
        self._queue.flush()

    def close(self) -> None:
        """Flush the queue and close the underlying httpx client."""
        try:
            self._queue.close()
        except Exception:
            pass
        if not self.is_closed:
            try:
                self._http_client.close()
            except Exception:
                pass
