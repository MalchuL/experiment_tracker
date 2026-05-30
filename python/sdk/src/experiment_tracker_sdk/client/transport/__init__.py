"""HTTP transport layer for the SDK client.

All synchronous requests flow through :class:`~experiment_tracker_sdk.client.transport.executor.HttpRequestExecutor`.
Public surface: :class:`RequestOptions` and :func:`resolve_stream`.
"""

from .options import RequestOptions, resolve_stream

__all__ = ["RequestOptions", "resolve_stream"]
