from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from .utils import log_error_response
import httpx

from .queue import RequestItem, RequestQueue
from ..logger import logger
from pydantic import BaseModel


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
        method: str,
        path: str,
        json: dict[str, Any] | BaseModel | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Enqueue a request to be sent in the background.

        Args:
            method: HTTP method.
            path: API path.
            json: JSON payload.
        """
        if isinstance(json, BaseModel):
            json = json.model_dump(exclude_unset=True)
        self._queue.enqueue(
            RequestItem(method=method, path=path, json=json, params=params)
        )

    def request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | BaseModel | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send a request and wait for the response.

        Args:
            method: HTTP method.
            path: API path.
            json: JSON payload.
        """
        if isinstance(json, BaseModel):
            json = json.model_dump(exclude_unset=True)
        response = self._client.request(method, path, json=json, params=params)
        _raise_for_status(response, self._supress_errors)
        return response
