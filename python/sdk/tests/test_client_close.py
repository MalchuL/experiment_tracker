from __future__ import annotations

from experiment_tracker_sdk.client.client import ExperimentTrackerClient


class _FailingClose:
    @property
    def is_closed(self) -> bool:
        return False

    def close(self) -> None:
        raise RuntimeError("already closed")


class _ClosedHttpClient:
    def __init__(self) -> None:
        self.close_called = False

    @property
    def is_closed(self) -> bool:
        return True

    def close(self) -> None:
        self.close_called = True


def test_experiment_tracker_client_close_ignores_queue_and_http_errors() -> None:
    client = object.__new__(ExperimentTrackerClient)
    client._queue = _FailingClose()
    client._http_client = _FailingClose()

    client.close()


def test_experiment_tracker_client_close_skips_closed_http_client() -> None:
    client = object.__new__(ExperimentTrackerClient)
    http_client = _ClosedHttpClient()
    client._queue = _FailingClose()
    client._http_client = http_client

    client.close()

    assert http_client.close_called is False
