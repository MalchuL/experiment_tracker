"""Controller tests for objects API."""

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
async def test_log_object_404_when_table_missing(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    resp = await http_client.post(
        f"/api/objects/log/{project_id}/{experiment_id}",
        json={
            "name": "sample",
            "object_type": "image",
            "path": "/artifacts/img.png",
            "step": 1,
            "metadata": None,
            "tags": None,
        },
    )
    assert resp.status_code == 404
    assert "table does not exist" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_log_object_success(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    resp = await http_client.post(
        f"/api/objects/log/{project_id}/{experiment_id}",
        json={
            "name": "sample_image",
            "object_type": "image",
            "path": "/artifacts/img.png",
            "step": 1,
            "metadata": {"width": "256"},
            "tags": ["train"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged"


@pytest.mark.asyncio
async def test_log_objects_batch_success(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    resp = await http_client.post(
        f"/api/objects/log_batch/{project_id}/{experiment_id}",
        json={
            "objects": [
                {
                    "name": "img1",
                    "object_type": "image",
                    "path": "/artifacts/1.png",
                    "step": 1,
                    "metadata": None,
                    "tags": None,
                },
                {
                    "name": "img2",
                    "object_type": "image",
                    "path": "/artifacts/2.png",
                    "step": 2,
                    "metadata": None,
                    "tags": None,
                },
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged"


@pytest.mark.asyncio
async def test_get_objects_empty_when_no_table(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    resp = await http_client.get(f"/api/objects/get/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_get_objects_returns_logged_data(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    await http_client.post(
        f"/api/objects/log/{project_id}/{experiment_id}",
        json={
            "name": "sample",
            "object_type": "image",
            "path": "/artifacts/img.png",
            "step": 1,
            "metadata": None,
            "tags": None,
        },
    )
    resp = await http_client.get(f"/api/objects/get/{project_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["experiment_id"] == str(experiment_id)
    assert len(data[0]["objects"]) == 1
    obj = data[0]["objects"][0]
    assert obj["name"] == "sample"
    assert obj["object_type"] == "image"
    assert obj["path"] == "/artifacts/img.png"
    assert obj["step"] == 1
