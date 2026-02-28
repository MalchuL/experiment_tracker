"""Controller tests for scalars API."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_with_tables(clickhouse_url: str, http_client: AsyncClient) -> tuple:
    project_id = uuid4()
    experiment_id = uuid4()
    await http_client.post("/api/projects", json={"project_id": str(project_id)})
    return project_id, experiment_id


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
