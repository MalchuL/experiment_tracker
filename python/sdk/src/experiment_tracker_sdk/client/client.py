from __future__ import annotations

from typing import Any, TypeVar

from .utils import log_error_response
import httpx

from .queue import RequestItem, RequestQueue
from .request import RequestSpec
from ..logger import logger
from pydantic import BaseModel

ResponseT = TypeVar("ResponseT")


def _raise_for_status(response: httpx.Response, supress_errors: bool) -> None:
    log_error_response(response, logger)
    if not supress_errors:
        response.raise_for_status()


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
        request: RequestSpec[Any],
    ) -> None:
        """Enqueue a request to be sent in the background.

        Args:
            request: RequestSpec describing request parameters.
        """
        payload = request.dto
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(exclude_unset=True)
        self._queue.enqueue(
            RequestItem(
                method=request.method,
                path=request.endpoint,
                json=payload,
                params=request.params,
            )
        )

    def request(
        self,
        request: RequestSpec[ResponseT],
    ) -> ResponseT | list[ResponseT] | dict[str, Any]:
        """Send a request and wait for the response.

        Args:
            request: RequestSpec describing request parameters.
        """
        payload = request.dto
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(exclude_unset=True)
        response = self._client.request(
            request.method, request.endpoint, json=payload, params=request.params
        )
        _raise_for_status(response, self._supress_errors)

        body = response.json()
        if request.returning_dto is None:
            return body

        if request.returning_dto_is_list:
            return [request.returning_dto.model_validate(item) for item in body]
        return request.returning_dto.model_validate(body)

    def flush(self) -> None:
        """Flush the request queue."""
        self._queue.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        self._queue.close()
        self._client.close()
