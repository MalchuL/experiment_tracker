"""Controller tests for scalars API."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_log_scalar_creates_table_when_missing(clickhouse_url: str, http_client: AsyncClient) -> None:
    """Logging without pre-created project table creates tables on-the-fly and succeeds."""
    project_id = uuid4()
    experiment_id = uuid4()
    resp = await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_id}",
        json={"scalars": {"loss": 0.5}, "step": 1, "tags": None},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged"


@pytest.mark.asyncio
async def test_log_scalar_success(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    resp = await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_id}",
        json={"scalars": {"loss": 0.5, "acc": 0.9}, "step": 1, "tags": None},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged"


@pytest.mark.asyncio
async def test_log_scalars_batch_success(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    resp = await http_client.post(
        f"/api/scalars/log_batch/{project_id}/{experiment_id}",
        json={
            "scalars": [
                {"scalars": {"loss": 0.5}, "step": 1, "tags": None},
                {"scalars": {"loss": 0.4}, "step": 2, "tags": None},
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged"


@pytest.mark.asyncio
async def test_get_scalars_empty_when_no_table(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    resp = await http_client.get(f"/api/scalars/get/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_get_scalars_uniform_max_points_caps_series(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, experiment_id = project_with_tables
    for step in range(1, 21):
        await http_client.post(
            f"/api/scalars/log/{project_id}/{experiment_id}",
            json={"scalars": {"loss": float(step)}, "step": step, "tags": None},
        )
    resp = await http_client.get(
        f"/api/scalars/get/{project_id}?max_points=5&sampling=uniform"
    )
    assert resp.status_code == 200
    xs = resp.json()["data"][0]["scalars"]["loss"]["x"]
    assert len(xs) == 5
    assert set(xs).issubset(set(range(1, 21)))
    assert xs[-1] == 20


@pytest.mark.asyncio
async def test_get_scalars_uniform_max_points_one_returns_latest(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, experiment_id = project_with_tables
    for step in range(1, 6):
        await http_client.post(
            f"/api/scalars/log/{project_id}/{experiment_id}",
            json={"scalars": {"loss": float(step)}, "step": step, "tags": None},
        )
    resp = await http_client.get(
        f"/api/scalars/get/{project_id}?max_points=1&sampling=uniform"
    )
    assert resp.status_code == 200
    series = resp.json()["data"][0]["scalars"]["loss"]
    assert series["x"] == [5]
    assert series["y"] == [5.0]


@pytest.mark.asyncio
async def test_get_scalars_returns_logged_data(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_id}",
        json={"scalars": {"loss": 0.5}, "step": 1, "tags": None},
    )
    resp = await http_client.get(f"/api/scalars/get/{project_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["experiment_id"] == str(experiment_id)
    assert "loss" in data[0]["scalars"]
    assert data[0]["scalars"]["loss"]["x"] == [1]
    assert data[0]["scalars"]["loss"]["y"] == [0.5]


@pytest.mark.asyncio
async def test_get_scalars_applies_limit_offset_to_grouped_results(
    clickhouse_url: str, http_client: AsyncClient
) -> None:
    project_id = uuid4()
    experiment_a = uuid4()
    experiment_b = uuid4()
    await http_client.post("/api/projects", json={"project_id": str(project_id)})
    await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_a}",
        json={"scalars": {"loss": 0.5}, "step": 1, "tags": None},
    )
    await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_b}",
        json={"scalars": {"loss": 0.4}, "step": 1, "tags": None},
    )

    resp = await http_client.get(f"/api/scalars/get/{project_id}?limit=1&offset=1")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["size"] == 1
    assert payload["has_next"] is False
    assert len(payload["data"]) == 1


@pytest.mark.asyncio
async def test_get_last_logged_experiments_empty(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, _ = project_with_tables
    resp = await http_client.post(
        f"/api/last_logged/{project_id}",
        json={"experiment_ids": None},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_get_last_logged_experiments_after_log(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_id}",
        json={"scalars": {"loss": 0.5}, "step": 1, "tags": None},
    )
    resp = await http_client.post(
        f"/api/last_logged/{project_id}",
        json={"experiment_ids": [str(experiment_id)]},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["experiment_id"] == str(experiment_id)
    assert "last_modified" in data[0]


@pytest.mark.asyncio
async def test_get_last_logged_experiments_applies_limit_offset(
    clickhouse_url: str, http_client: AsyncClient
) -> None:
    project_id = uuid4()
    experiment_a = uuid4()
    experiment_b = uuid4()
    await http_client.post("/api/projects", json={"project_id": str(project_id)})
    await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_a}",
        json={"scalars": {"loss": 0.5}, "step": 1, "tags": None},
    )
    await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_b}",
        json={"scalars": {"loss": 0.4}, "step": 1, "tags": None},
    )

    resp = await http_client.post(
        f"/api/last_logged/{project_id}?limit=1&offset=0",
        json={"experiment_ids": None},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["size"] == 1
    assert payload["has_next"] is True
