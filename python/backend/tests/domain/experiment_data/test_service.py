from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from clients.object_storage import SnapshotFileEntryDTO, SnapshotManifestResponseDTO
from domain.experiment_data.service import ExperimentDataService
from models import ExperimentDataType


class FakeExperimentRepository:
    def __init__(self, project_id):
        self.project_id = project_id

    async def get_by_id(self, experiment_id):
        return SimpleNamespace(id=experiment_id, project_id=self.project_id)


class FakeExperimentDataRepository:
    def __init__(self, snapshot_id):
        self.snapshot_id = snapshot_id

    async def get_by_experiment_and_type(self, experiment_id, data_type):
        assert data_type is ExperimentDataType.SNAPSHOT
        if self.snapshot_id is None:
            return None
        return SimpleNamespace(
            id=uuid4(),
            experiment_id=experiment_id,
            data={"snapshot_id": str(self.snapshot_id)},
            created_at=None,
            updated_at=None,
        )


class FakeProjectArtifactsService:
    def __init__(self, project_id, snapshot_id):
        self.project_id = project_id
        self.snapshot_id = snapshot_id

    async def ensure_view_project_artifacts(self, user, project_id):
        assert project_id == self.project_id

    async def ensure_log_project_artifacts(self, user, project_id):
        assert project_id == self.project_id

    async def get_project_snapshot_manifest(self, user, project_id, snapshot_id):
        assert project_id == self.project_id
        assert snapshot_id == self.snapshot_id
        return SnapshotManifestResponseDTO(
            snapshot_id=snapshot_id,
            files=[
                SnapshotFileEntryDTO(
                    path="src/train.py",
                    hash="a" * 64,
                    size=12,
                )
            ],
        )

    async def download_project_artifact(self, user, project_id, artifact_hash):
        assert artifact_hash == "a" * 64
        return b"print('ok')\n"


@pytest.mark.asyncio
async def test_get_experiment_snapshot_files_returns_single_manifest_with_size() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    snapshot_id = uuid4()
    service = ExperimentDataService(
        FakeExperimentRepository(project_id),
        FakeExperimentDataRepository(snapshot_id),
        FakeProjectArtifactsService(project_id, snapshot_id),
    )

    result = await service.get_experiment_snapshot_files(
        SimpleNamespace(id=uuid4()),
        experiment_id,
    )

    assert result.experiment_id == experiment_id
    assert result.snapshot_id == snapshot_id
    assert result.files[0].path == "src/train.py"
    assert result.files[0].hash == "a" * 64
    assert result.files[0].size == 12

