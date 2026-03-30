from __future__ import annotations

from typing import Any, TypeVar
from pathlib import Path

from .utils.logging import disable_httpx_logging

from .utils import log_error_response
import httpx

from .queue import RequestItem, RequestQueue
from .request import ApiRequestSpec
from ..logger import logger
from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


def _raise_for_status(response: httpx.Response, supress_errors: bool) -> None:
    try:
        response.raise_for_status()
    except Exception:  # noqa: BLE001
        log_error_response(response, logger)
        if not supress_errors:
            raise


class ExperimentTrackerClient:
    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = 30.0,
        max_queue_size: int = 1000,
        supress_errors: bool = False,
    ):
        """Initialize a synchronous SDK client for Experiment Tracker.

        Args:
            base_url: Backend base URL, e.g. "http://127.0.0.1:8000".
            api_token: API token used for Authorization header.
            timeout: HTTP timeout (seconds) for requests.
            max_queue_size: Max queued metric requests before blocking.

        Example:
            client = ExperimentTrackerClient(
                base_url="http://127.0.0.1:8000",
                api_token="my-token",
            )
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_token}"},
        )
        self._queue = RequestQueue(self._client, max_queue_size=max_queue_size)
        self._supress_errors = supress_errors

    def queued_request(
        self,
        request_spec: ApiRequestSpec[Any],
    ) -> None:
        """Enqueue a request to be sent in the background.

        Args:
            request_spec: ApiRequestSpec describing request parameters.
        """
        payload = request_spec.request_payload
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(exclude_unset=True)
        self._queue.enqueue(
            RequestItem(
                method=request_spec.method,
                path=request_spec.endpoint,
                json=payload,
                params=request_spec.query_params,
            )
        )

    def request(
        self,
        request_spec: ApiRequestSpec[ResponseT],
    ) -> ResponseT | list[ResponseT] | dict[str, Any]:
        """Send a request and wait for the response.

        Args:
            request_spec: ApiRequestSpec describing request parameters.
        """
        payload = request_spec.request_payload
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(exclude_unset=True)
        with disable_httpx_logging():
            response = self._client.request(
                request_spec.method,
                request_spec.endpoint,
                json=payload,
                params=request_spec.query_params,
            )
        _raise_for_status(response, self._supress_errors)

        body = response.json()
        if request_spec.response_model is None:
            return body

        if request_spec.response_is_list:
            return [request_spec.response_model.model_validate(item) for item in body]
        return request_spec.response_model.model_validate(body)

    def request_json(
        self,
        method: str,
        path: str,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with disable_httpx_logging():
            response = self._client.request(
                method,
                path,
                json=json,
                params=params,
            )
        _raise_for_status(response, self._supress_errors)
        return response.json()

    def upload_file(
        self,
        endpoint: str,
        params: dict[str, Any],
        file_name: str,
        file_content: bytes,
        content_type: str = "application/octet-stream",
        form_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upload file to backend endpoint.

        Args:
            endpoint: The endpoint to upload the file to.
            params: The parameters to pass to the URI path of the endpoint.
            file_name: The name of the file to upload.
            file_content: The content of the file to upload.
            content_type: The content type of the file to upload (request still will use multipart/form-data for file upload).
            form_data: The form data to pass to the endpoint (backend will parse as Form data this params (not JSON)).
        """
        with disable_httpx_logging():
            # This request still uses multipart/form-data for file upload.
            response = self._client.request(
                "POST",
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
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> bytes:
        """Download raw file bytes from backend endpoint.

        Args:
            endpoint: The endpoint to download the file from.
            params: The parameters to pass to the URI path of the endpoint.
        """
        with disable_httpx_logging():
            response = self._client.request(
                "GET",
                endpoint,
                params=params,
            )
        _raise_for_status(response, self._supress_errors)
        return response.content

    def download_file_to_path(
        self,
        endpoint: str,
        output_path: str | Path,
        params: dict[str, Any] | None = None,
    ) -> Path:
        """Download bytes and persist them to local filesystem.

        Args:
            endpoint: The endpoint to download the file from.
            output_path: The path to save the file to.
            params: The parameters to pass to the URI path of the endpoint.
        """
        content = self.download_file(endpoint=endpoint, params=params)
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return destination

    def flush(self) -> None:
        """Flush the request queue."""
        self._queue.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        self._queue.close()
        self._client.close()
