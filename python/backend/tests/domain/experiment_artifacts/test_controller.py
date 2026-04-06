from __future__ import annotations

import io
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.auth import get_current_user_dual
from api.routes.service_dependencies import get_experiment_artifacts_service
from domain.experiment_artifacts.controller import router as experiment_artifacts_router
from domain.experiment_artifacts.dto import (
    ExperimentArtifactDownloadDTO,
    ExperimentArtifactDTO,
    ExperimentArtifactsDeleteResponseDTO,
)
from domain.experiment_artifacts.error import ExperimentArtifactNotFoundError


class FakeArtifactsService:
    async def upsert_experiment_artifact(
        self, user, experiment_id, name, filepath, file
    ) -> ExperimentArtifactDTO:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return ExperimentArtifactDTO(
            id=uuid4(),
            experiment_id=experiment_id,
            name=name,
            filepath=filepath,
            filename=file.filename or "artifact.bin",
            mime_type=file.content_type or "application/octet-stream",
            storage_path="named/path",
            created_at=now,
            updated_at=now,
        )

    async def get_experiment_artifact(
        self, user, experiment_id, filepath=None, blob_id=None, artifact_hash=None
    ):
        raise ExperimentArtifactNotFoundError("not found")

    async def download_experiment_artifact(
        self, user, experiment_id, filepath=None, blob_id=None, artifact_hash=None
    ):
        return ExperimentArtifactDownloadDTO(
            content=b"payload",
            content_type="application/octet-stream",
            filename="artifact.bin",
        )

    async def download_experiment_artifacts_archive(self, user, experiment_id, name):
        raise ExperimentArtifactNotFoundError("archive not found")

    async def delete_experiment_artifacts(
        self,
        user,
        experiment_id,
        filepath=None,
        blob_id=None,
        artifact_hash=None,
    ) -> ExperimentArtifactsDeleteResponseDTO:
        return ExperimentArtifactsDeleteResponseDTO(deleted_count=1)


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(experiment_artifacts_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_user) -> TestClient:
    app = create_test_app()

    async def override_current_user():
        return test_user

    async def override_service():
        return FakeArtifactsService()

    app.dependency_overrides[get_current_user_dual] = override_current_user
    app.dependency_overrides[get_experiment_artifacts_service] = override_service
    return TestClient(app)


def test_upsert_artifact_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/experiment-artifacts/upsert",
        data={
            "experiment_id": str(uuid4()),
            "name": "configs",
            "filepath": "train/config.yaml",
        },
        files={"file": ("config.yaml", io.BytesIO(b"cfg"), "text/yaml")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "configs"
    assert payload["filepath"] == "train/config.yaml"


def test_get_artifact_not_found_maps_to_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/experiment-artifacts/get",
        params={
            "experiment_id": str(uuid4()),
            "filepath": "missing.yaml",
        },
    )

    assert response.status_code == 404
