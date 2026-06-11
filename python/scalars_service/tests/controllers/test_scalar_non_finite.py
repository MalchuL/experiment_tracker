"""Round-trip tests for non-finite scalar wire values."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_log_and_get_non_finite_scalars(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, experiment_id = project_with_tables
    cases = [
        (1, {"nan_metric": "nan"}),
        (2, {"inf_metric": "inf"}),
        (3, {"neg_inf_metric": "-inf"}),
    ]
    for step, scalars in cases:
        resp = await http_client.post(
            f"/api/scalars/log/{project_id}/{experiment_id}",
            json={"scalars": scalars, "step": step, "tags": None},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged"

    get_resp = await http_client.get(f"/api/scalars/get/{project_id}")
    assert get_resp.status_code == 200
    payload = get_resp.json()["data"][0]["scalars"]
    assert payload["nan_metric"] == {"x": [1], "y": ["nan"]}
    assert payload["inf_metric"] == {"x": [2], "y": ["inf"]}
    assert payload["neg_inf_metric"] == {"x": [3], "y": ["-inf"]}


@pytest.mark.asyncio
async def test_log_and_get_mixed_finite_and_non_finite_series(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, experiment_id = project_with_tables
    series = [
        (1, {"loss": 0.5}),
        (2, {"loss": "nan"}),
        (3, {"loss": 0.25}),
        (4, {"loss": "inf"}),
        (5, {"loss": 0.1}),
    ]
    for step, scalars in series:
        resp = await http_client.post(
            f"/api/scalars/log/{project_id}/{experiment_id}",
            json={"scalars": scalars, "step": step, "tags": None},
        )
        assert resp.status_code == 200

    get_resp = await http_client.get(f"/api/scalars/get/{project_id}")
    assert get_resp.status_code == 200
    loss = get_resp.json()["data"][0]["scalars"]["loss"]
    assert loss["x"] == [1, 2, 3, 4, 5]
    assert loss["y"] == [0.5, "nan", 0.25, "inf", 0.1]
