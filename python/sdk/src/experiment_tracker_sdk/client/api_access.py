"""Process-wide access point for SDK API clients and request registries."""

from __future__ import annotations

from dataclasses import dataclass
import threading
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

    Use :meth:`instance` to obtain the shared object, then call
    :meth:`get_api_requests_registry` or :meth:`get_request_client` before
    issuing typed requests via :meth:`ExperimentTrackerClient.request`.
    """

    _instance: ClassVar[ExpTrackerApiAccess | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        """Create an API access object.

        Callers should normally use :meth:`instance` so the SDK keeps one
        process-wide construction point.
        """

    @classmethod
    def instance(cls) -> ExpTrackerApiAccess:
        """Return the process-wide API access object.

        Returns:
            Shared :class:`ExpTrackerApiAccess` instance.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_api_requests_registry(self) -> APIRequestsRegistry:
        """Build a new SDK request-spec registry.

        Returns:
            Registry containing request-spec factories for all SDK domains.
        """
        return APIRequestsRegistry()

    def get_request_client(self) -> ExperimentTrackerClient:
        """Build an SDK HTTP client from saved configuration.

        Returns:
            Configured :class:`ExperimentTrackerClient`.

        Raises:
            ExpTrackerConfigError: If SDK config has not been initialized.
        """
        config = load_config()
        return ExperimentTrackerClient(
            config.base_url,
            config.api_token,
            api_prefix=config.api_prefix,
        )


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
        request_client=request_client or access.get_request_client(),
        api_requests_registry=(
            api_requests_registry or access.get_api_requests_registry()
        ),
    )
