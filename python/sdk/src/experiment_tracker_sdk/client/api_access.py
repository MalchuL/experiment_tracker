"""Process-wide access point for SDK API clients and request registries."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import ClassVar

from experiment_tracker_sdk.config import load_config

from .api_registry import APIRequestsRegistry
from .client import ExperimentTrackerClient


@dataclass(frozen=True)
class ResolvedClientAndRegistry:
    """Resolved SDK request dependencies.

    Args:
        request_client: SDK HTTP client used to execute request specs.
        api_requests_registry: Registry that builds request specs for SDK
            domains.
    """

    request_client: ExperimentTrackerClient
    api_requests_registry: APIRequestsRegistry


class ExpTrackerApiAccess:
    """Singleton that builds SDK request dependencies from saved config.

    Use :meth:`instance` to obtain the shared object, then use
    :attr:`api_requests_registry` and :attr:`request_client` before issuing
    typed requests via :meth:`ExperimentTrackerClient.request`.
    """

    _instance: ClassVar[ExpTrackerApiAccess | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        api_requests_registry: APIRequestsRegistry,
        request_client: ExperimentTrackerClient,
    ) -> None:
        """Create an API access object.

        Callers should normally use :meth:`instance` so the SDK keeps one
        process-wide construction point.
        """
        self._api_requests_registry = api_requests_registry
        self._request_client = request_client

    @classmethod
    def _create(cls) -> ExpTrackerApiAccess:
        api_requests_registry = APIRequestsRegistry()
        config = load_config()
        request_client = ExperimentTrackerClient(
            config.base_url,
            config.api_token,
            api_prefix=config.api_prefix,
        )
        return cls(api_requests_registry, request_client)

    @classmethod
    def instance(cls) -> ExpTrackerApiAccess:
        """Return the process-wide API access object.

        Returns:
            Shared :class:`ExpTrackerApiAccess` instance.
        """
        with cls._lock:
            if cls._instance is None or cls._instance.request_client.is_closed:
                cls._instance = cls._create()
            return cls._instance

    @classmethod
    def reset(cls) -> ExpTrackerApiAccess:
        """Replace the process-wide API access object with a newly configured one.

        Returns:
            The new shared :class:`ExpTrackerApiAccess` instance.
        """
        with cls._lock:
            previous = cls._instance
            cls._instance = cls._create()
        if previous is not None:
            try:
                previous.request_client.close()
            except Exception:
                pass
        return cls._instance

    @property
    def api_requests_registry(self) -> APIRequestsRegistry:
        """Return the process-wide SDK request-spec registry.

        Returns:
            Registry containing request-spec factories for all SDK domains.
        """
        return self._api_requests_registry

    @property
    def request_client(self) -> ExperimentTrackerClient:
        """Return the process-wide SDK HTTP client.

        Returns:
            Configured :class:`ExperimentTrackerClient`.

        Raises:
            ExpTrackerConfigError: If SDK config has not been initialized.
        """
        return self._request_client


def resolve_client_and_registry(
    request_client: ExperimentTrackerClient | None = None,
    api_requests_registry: APIRequestsRegistry | None = None,
) -> ResolvedClientAndRegistry:
    """Resolve optional SDK request dependencies.

    Args:
        request_client: Optional SDK HTTP client. When omitted, a configured
            client is created from :class:`ExpTrackerApiAccess`.
        api_requests_registry: Optional request-spec registry. When omitted, a
            new registry is created from :class:`ExpTrackerApiAccess`.

    Returns:
        :class:`ResolvedClientAndRegistry` with named request dependencies ready
        for typed SDK requests.
    """
    access = ExpTrackerApiAccess.instance()
    return ResolvedClientAndRegistry(
        request_client=request_client or access.request_client,
        api_requests_registry=api_requests_registry or access.api_requests_registry,
    )
