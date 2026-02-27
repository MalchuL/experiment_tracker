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
    assert data["project_id"] == str(project_id)
    assert "scalars_" in data["table_name"]


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
