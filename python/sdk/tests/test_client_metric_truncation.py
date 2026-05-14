import logging

import pytest

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry


def test_metric_upsert_truncates_long_name(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    reg = APIRequestsRegistry()
    long_name = "m" * 700
    spec = reg.metrics.upsert_metric(
        experiment_id="223e4567-e89b-12d3-a456-426614174000",
        name=long_name,
        value=1.0,
        label=None,
    )
    assert spec.request_payload is not None
    dumped = spec.request_payload.model_dump(by_alias=True)
    assert len(dumped["name"]) == 512
    assert any("Metric name exceeded max length" in r.message for r in caplog.records)
