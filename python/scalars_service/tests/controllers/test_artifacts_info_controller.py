"""Controller tests for artifacts_info API."""

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
async def test_log_artifact_info_creates_table_when_missing(clickhouse_url: str, http_client: AsyncClient) -> None:
    """Logging without pre-created project table creates tables on-the-fly and succeeds."""
    project_id = uuid4()
    experiment_id = uuid4()
    resp = await http_client.post(
        f"/api/artifacts_info/log/{project_id}/{experiment_id}",
        json={
            "name": "sample",
            "artifact_type": "image",
            "path": "/artifacts/img.png",
            "step": 1,
            "metadata": None,
            "tags": None,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged"


@pytest.mark.asyncio
async def test_log_artifact_info_success(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    resp = await http_client.post(
        f"/api/artifacts_info/log/{project_id}/{experiment_id}",
        json={
            "name": "sample_image",
            "artifact_type": "image",
            "path": "/artifacts/img.png",
            "step": 1,
            "metadata": {"width": "256"},
            "tags": ["train"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged"


@pytest.mark.asyncio
async def test_log_artifact_info_batch_success(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    resp = await http_client.post(
        f"/api/artifacts_info/log_batch/{project_id}/{experiment_id}",
        json={
            "artifacts": [
                {
                    "name": "img1",
                    "artifact_type": "image",
                    "path": "/artifacts/1.png",
                    "step": 1,
                    "metadata": None,
                    "tags": None,
                },
                {
                    "name": "img2",
                    "artifact_type": "image",
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
async def test_get_artifact_info_empty_when_no_table(clickhouse_url: str, http_client: AsyncClient) -> None:
    project_id = uuid4()
    resp = await http_client.get(f"/api/artifacts_info/get/{project_id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["data"] == []
    assert payload["total"] == 0


@pytest.mark.asyncio
async def test_get_artifact_info_returns_logged_data(clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple) -> None:
    project_id, experiment_id = project_with_tables
    await http_client.post(
        f"/api/artifacts_info/log/{project_id}/{experiment_id}",
        json={
            "name": "sample",
            "artifact_type": "image",
            "path": "/artifacts/img.png",
            "step": 1,
            "metadata": None,
            "tags": None,
        },
    )
    resp = await http_client.get(f"/api/artifacts_info/get/{project_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["experiment_id"] == str(experiment_id)
    assert len(data[0]["artifacts_info"]) == 1
    artifact = data[0]["artifacts_info"][0]
    assert artifact["name"] == "sample"
    assert artifact["artifact_type"] == "image"
    assert artifact["path"] == "/artifacts/img.png"
    assert artifact["step"] == 1


@pytest.mark.asyncio
async def test_get_artifact_info_applies_limit_offset(
    clickhouse_url: str, http_client: AsyncClient, project_with_tables: tuple
) -> None:
    project_id, experiment_id = project_with_tables
    experiment_b = uuid4()
    await http_client.post(
        f"/api/artifacts_info/log/{project_id}/{experiment_id}",
        json={
            "name": "sample-a",
            "artifact_type": "image",
            "path": "/artifacts/a.png",
            "step": 1,
            "metadata": None,
            "tags": None,
        },
    )
    await http_client.post(
        f"/api/artifacts_info/log/{project_id}/{experiment_b}",
        json={
            "name": "sample-b",
            "artifact_type": "image",
            "path": "/artifacts/b.png",
            "step": 1,
            "metadata": None,
            "tags": None,
        },
    )
    resp = await http_client.get(f"/api/artifacts_info/get/{project_id}?limit=1&offset=0")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["size"] == 1
    assert payload["has_next"] is True
    assert payload["total"] == 2


@pytest.mark.asyncio
async def test_log_artifact_info_updates_last_logged(clickhouse_url: str, http_client: AsyncClient) -> None:
    """Logging an artifact without pre-created tables creates them and updates last_logged."""
    project_id = uuid4()
    experiment_id = uuid4()
    await http_client.post(
        f"/api/artifacts_info/log/{project_id}/{experiment_id}",
        json={
            "name": "sample",
            "artifact_type": "image",
            "path": "/artifacts/img.png",
            "step": 1,
            "metadata": None,
            "tags": None,
        },
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
