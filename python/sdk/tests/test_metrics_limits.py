import logging

import pytest

from experiment_tracker_sdk.client.domain.metrics.limits import truncate_metric_name


def test_truncate_metric_name_warns_and_shortens(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    out = truncate_metric_name("a" * 700)
    assert len(out) == 512
    assert any("Metric name exceeded max length" in r.message for r in caplog.records)
