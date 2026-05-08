"""Controller tests for projects API."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project_returns_table_name(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    resp = await http_client.post("/api/projects", json={"project_id": str(project_id)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["projectId"] == str(project_id)
    assert "scalars_" in data["tableName"]


@pytest.mark.asyncio
async def test_exists_returns_false_for_missing_project(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    resp = await http_client.get(f"/api/projects/exists/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["exists"] is False


@pytest.mark.asyncio
async def test_exists_returns_true_after_create(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    await http_client.post("/api/projects", json={"project_id": str(project_id)})
    resp = await http_client.get(f"/api/projects/exists/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["exists"] is True


@pytest.mark.asyncio
async def test_experiments_returns_empty_for_new_project(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    await http_client.post("/api/projects", json={"project_id": str(project_id)})
    resp = await http_client.get(f"/api/projects/experiments/{project_id}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_delete_project_succeeds(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    await http_client.post("/api/projects", json={"project_id": str(project_id)})
    resp = await http_client.delete(f"/api/projects/{project_id}")
    assert resp.status_code == 200, f"Delete failed: {resp.status_code} {resp.json()}"
    assert "deleted" in resp.json()["message"].lower()

    exists_resp = await http_client.get(f"/api/projects/exists/{project_id}")
    assert exists_resp.status_code == 200
    assert exists_resp.json()["exists"] is False


@pytest.mark.asyncio
async def test_get_project_usage_after_create(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    await http_client.post("/api/projects", json={"project_id": str(project_id)})
    resp = await http_client.get(f"/api/projects/{project_id}/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["projectId"] == str(project_id)
    assert "totalBytes" in data
    assert len(data["tables"]) == 3
    names = {t["table"] for t in data["tables"]}
    assert any(n.startswith("scalars_") for n in names)
    assert any(n.startswith("artifacts_info_") for n in names)
    assert any("last_logged" in n for n in names)
    assert all(t["exists"] is True for t in data["tables"])


@pytest.mark.asyncio
async def test_get_experiment_usage_after_logging(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, experiment_id = project_with_tables
    await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_id}",
        json={"scalars": {"loss": 1.0}, "step": 1, "tags": None},
    )
    resp = await http_client.get(
        f"/api/projects/{project_id}/experiments/{experiment_id}/usage"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["projectId"] == str(project_id)
    assert body["experimentId"] == str(experiment_id)
    assert body["rows"] >= 1
    assert body["bytes"] >= 0


@pytest.mark.asyncio
async def test_delete_experiment_data_removes_scalars_rows(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, experiment_id = project_with_tables
    await http_client.post(
        f"/api/scalars/log/{project_id}/{experiment_id}",
        json={"scalars": {"loss": 0.5}, "step": 1, "tags": None},
    )
    before = await http_client.get(f"/api/scalars/get/{project_id}")
    assert before.status_code == 200
    assert len(before.json()["data"]) >= 1
    assert "loss" in before.json()["data"][0].get("scalars", {})

    del_resp = await http_client.delete(
        f"/api/projects/{project_id}/experiments/{experiment_id}"
    )
    assert del_resp.status_code == 200
    assert del_resp.json().get("deleted") is True

    usage = await http_client.get(
        f"/api/projects/{project_id}/experiments/{experiment_id}/usage"
    )
    assert usage.status_code == 200
    assert usage.json()["rows"] == 0
    assert usage.json()["bytes"] == 0


@pytest.mark.asyncio
async def test_delete_experiment_data_removes_artifacts_info_rows(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, experiment_id = project_with_tables
    log_resp = await http_client.post(
        f"/api/artifacts_info/log/{project_id}/{experiment_id}",
        json={
            "name": "img",
            "artifact_type": "image",
            "path": "abc123",
            "step": 1,
            "metadata": {},
            "tags": [],
        },
    )
    assert log_resp.status_code == 200
    before = await http_client.get(
        f"/api/artifacts_info/get/{project_id}",
        params={"experiment_id": str(experiment_id)},
    )
    assert before.status_code == 200
    assert before.json()["total"] >= 1

    await http_client.delete(f"/api/projects/{project_id}/experiments/{experiment_id}")

    after = await http_client.get(
        f"/api/artifacts_info/get/{project_id}",
        params={"experiment_id": str(experiment_id)},
    )
    assert after.status_code == 200
    assert after.json()["data"] == []


@pytest.mark.asyncio
async def test_list_storage_tables_includes_project_tables(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, _ = project_with_tables
    hex_part = str(project_id).replace("-", "")
    resp = await http_client.get("/api/projects/admin/storage/tables", params={"limit": 100})
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()["tables"]}
    assert any(hex_part.lower() in n.lower() for n in names)


@pytest.mark.asyncio
async def test_compact_columns_route_still_on_scalars_router(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, _ = project_with_tables
    resp = await http_client.post(f"/api/scalars/projects/{project_id}/compact-columns")
    assert resp.status_code == 200
    assert "droppedColumns" in resp.json()
