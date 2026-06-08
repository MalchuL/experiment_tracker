"""Contract tests for translating main-backend responses into analysis data."""

from uuid import uuid4

import pytest

from mltools.clients.backend.client import BackendClient
from mltools.domain.hparam_importance.dto import TargetMetricDTO


@pytest.mark.asyncio
async def test_backend_client_reads_backend_camel_case_pages(monkeypatch) -> None:
    experiment_id = uuid4()
    pages = [
        {"data": [{"id": str(experiment_id), "name": "run"}], "hasNext": False},
        {
            "data": [
                {
                    "experimentId": str(experiment_id),
                    "name": "loss",
                    "label": None,
                    "value": 0.5,
                }
            ],
            "hasNext": False,
        },
    ]

    async def request(self, method, path, **kwargs):
        return pages.pop(0)

    monkeypatch.setattr(BackendClient, "_request", request)
    client = BackendClient()

    experiments = await client.list_experiments(uuid4())
    metrics = await client.get_aggregated_metrics(
        uuid4(), [TargetMetricDTO(name="loss")]
    )

    assert experiments[0]["id"] == str(experiment_id)
    assert metrics[("loss", None)][experiment_id] == 0.5
