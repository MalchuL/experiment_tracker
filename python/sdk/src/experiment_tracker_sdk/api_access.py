"""Process-wide access point for API registry and HTTP client construction."""

from __future__ import annotations

import threading
from typing import ClassVar

from experiment_tracker_sdk.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.config import load_config


class ExpTrackerApiAccess:
    """Singleton matching :class:`~experiment_tracker_sdk.exp_tracker.ExpTracker`
    ``_get_api_requests_registry`` / ``_get_request_client`` behavior.

    Use :meth:`instance` to obtain the shared object, then call
    :meth:`get_api_requests_registry` or :meth:`get_request_client` before
    issuing typed requests via :meth:`ExperimentTrackerClient.request`.
    """

    _instance: ClassVar[ExpTrackerApiAccess | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        """Not intended for direct construction; use :meth:`instance`."""

    @classmethod
    def instance(cls) -> ExpTrackerApiAccess:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_api_requests_registry(self) -> APIRequestsRegistry:
        return APIRequestsRegistry()

    def get_request_client(self) -> ExperimentTrackerClient:
        config = load_config()
        return ExperimentTrackerClient(
            config.base_url,
            config.api_token,
            api_prefix=config.api_prefix,
        )
