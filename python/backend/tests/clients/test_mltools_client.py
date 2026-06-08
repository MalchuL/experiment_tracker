"""Request-construction tests for the main backend's internal MLTools client."""

from uuid import uuid4

import httpx
import pytest

from clients.mltools.client import MLToolsClient
from clients.mltools.dto import MLToolsCreateJobDTO, MLToolsTargetMetricDTO


@pytest.mark.asyncio
async def test_create_job_request(monkeypatch) -> None:
    seen = {}

    async def request(self, method, url, **kwargs):
        seen.update(method=method, url=url, json=kwargs["json"])
        return httpx.Response(
            200,
            json={"job_id": str(uuid4()), "status": "pending"},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "request", request)
    client = MLToolsClient("http://mltools/internal/mltools")
    project_id = uuid4()

    await client.create_job(
        project_id,
        MLToolsCreateJobDTO(target_metrics=[MLToolsTargetMetricDTO(name="loss")]),
    )

    assert seen["url"].endswith(f"/projects/{project_id}/hparams/importance/jobs")
    assert seen["json"]["target_metrics"] == [{"name": "loss", "label": None}]
