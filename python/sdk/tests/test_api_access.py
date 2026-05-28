from __future__ import annotations

from types import SimpleNamespace


def test_api_access_reset_replaces_cached_client_and_registry(monkeypatch) -> None:
    from experiment_tracker_sdk.client import api_access

    clients = []
    registries = []
    configs = [
        SimpleNamespace(
            base_url="http://first",
            api_token="first-token",
            api_prefix="/api",
        ),
        SimpleNamespace(
            base_url="http://second",
            api_token="second-token",
            api_prefix="/v2",
        ),
    ]

    class FakeRegistry:
        def __init__(self) -> None:
            registries.append(self)

    class FakeClient:
        def __init__(self, base_url: str, api_token: str, api_prefix: str) -> None:
            self.base_url = base_url
            self.api_token = api_token
            self.api_prefix = api_prefix
            self.closed = False
            clients.append(self)

        def close(self) -> None:
            self.closed = True

        @property
        def is_closed(self) -> bool:
            return self.closed

    monkeypatch.setattr(api_access, "APIRequestsRegistry", FakeRegistry)
    monkeypatch.setattr(api_access, "ExperimentTrackerClient", FakeClient)
    monkeypatch.setattr(api_access, "load_config", lambda: configs.pop(0))
    monkeypatch.setattr(api_access.ExpTrackerApiAccess, "_instance", None)

    first = api_access.ExpTrackerApiAccess.instance()
    second = api_access.ExpTrackerApiAccess.reset()

    assert first is not second
    assert first.request_client.closed is True
    assert second.request_client.closed is False
    assert first.api_requests_registry is registries[0]
    assert second.api_requests_registry is registries[1]
    assert clients[0].base_url == "http://first"
    assert clients[0].api_token == "first-token"
    assert clients[0].api_prefix == "/api"
    assert clients[1].base_url == "http://second"
    assert clients[1].api_token == "second-token"
    assert clients[1].api_prefix == "/v2"
    assert api_access.ExpTrackerApiAccess.instance() is second

    monkeypatch.setattr(api_access.ExpTrackerApiAccess, "_instance", None)


def test_api_access_instance_recreates_closed_cached_client(monkeypatch) -> None:
    from experiment_tracker_sdk.client import api_access

    configs = [
        SimpleNamespace(
            base_url="http://first",
            api_token="first-token",
            api_prefix="/api",
        ),
        SimpleNamespace(
            base_url="http://second",
            api_token="second-token",
            api_prefix="/api",
        ),
    ]

    class FakeRegistry:
        pass

    class FakeClient:
        def __init__(self, base_url: str, api_token: str, api_prefix: str) -> None:
            self.base_url = base_url
            self.api_token = api_token
            self.api_prefix = api_prefix
            self.closed = False

        @property
        def is_closed(self) -> bool:
            return self.closed

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(api_access, "APIRequestsRegistry", FakeRegistry)
    monkeypatch.setattr(api_access, "ExperimentTrackerClient", FakeClient)
    monkeypatch.setattr(api_access, "load_config", lambda: configs.pop(0))
    monkeypatch.setattr(api_access.ExpTrackerApiAccess, "_instance", None)

    first = api_access.ExpTrackerApiAccess.instance()
    first.request_client.close()
    second = api_access.ExpTrackerApiAccess.instance()

    assert first is not second
    assert second.request_client.base_url == "http://second"

    monkeypatch.setattr(api_access.ExpTrackerApiAccess, "_instance", None)


def test_api_access_reset_ignores_previous_client_close_error(monkeypatch) -> None:
    from experiment_tracker_sdk.client import api_access

    configs = [
        SimpleNamespace(
            base_url="http://first",
            api_token="first-token",
            api_prefix="/api",
        ),
        SimpleNamespace(
            base_url="http://second",
            api_token="second-token",
            api_prefix="/api",
        ),
    ]

    class FakeRegistry:
        pass

    class FakeClient:
        def __init__(self, base_url: str, api_token: str, api_prefix: str) -> None:
            self.base_url = base_url
            self.api_token = api_token
            self.api_prefix = api_prefix

        def close(self) -> None:
            raise RuntimeError("already closed")

        @property
        def is_closed(self) -> bool:
            return False

    monkeypatch.setattr(api_access, "APIRequestsRegistry", FakeRegistry)
    monkeypatch.setattr(api_access, "ExperimentTrackerClient", FakeClient)
    monkeypatch.setattr(api_access, "load_config", lambda: configs.pop(0))
    monkeypatch.setattr(api_access.ExpTrackerApiAccess, "_instance", None)

    first = api_access.ExpTrackerApiAccess.instance()
    second = api_access.ExpTrackerApiAccess.reset()

    assert first is not second
    assert second.request_client.base_url == "http://second"

    monkeypatch.setattr(api_access.ExpTrackerApiAccess, "_instance", None)
