from __future__ import annotations

from uuid import uuid4

import pytest

from clients.object_storage import (
    ExperimentTrackedArtifactItemDTO,
    ExperimentTrackedUploadResponseDTO,
)
from domain.experiment_artifacts.mapper import ExperimentArtifactsMapper


def test_validate_artifact_name_rejects_slash() -> None:
    m = ExperimentArtifactsMapper()
    with pytest.raises(ValueError, match="Invalid artifact name"):
        m.validate_artifact_name("a/b")


def test_normalize_relative_filepath_rejects_absolute() -> None:
    m = ExperimentArtifactsMapper()
    with pytest.raises(ValueError, match="Invalid filepath"):
        m.normalize_relative_filepath("/etc/passwd")


def test_tracked_item_to_dto_keeps_full_filepath() -> None:
    m = ExperimentArtifactsMapper()
    experiment_id = uuid4()
    row_id = uuid4()
    item = ExperimentTrackedArtifactItemDTO(
        id=row_id,
        hash="ab" * 32,
        file_path="weights/epoch-1.pt",
        mime_type="application/octet-stream",
        size=10,
        metadata={"name": "weights"},
    )
    dto = m.tracked_item_to_dto(experiment_id, item)
    assert dto.id == row_id
    assert dto.experiment_id == experiment_id
    assert dto.name == "weights"
    assert dto.filepath == "weights/epoch-1.pt"
    assert dto.filename == "epoch-1.pt"
    assert dto.mime_type == "application/octet-stream"
    assert dto.storage_path == item.hash


def test_display_name_prefers_metadata_name() -> None:
    m = ExperimentArtifactsMapper()
    assert (
        m.display_name_for_tracked("weights/a.pt", {"name": "  my-label  "})
        == "my-label"
    )


def test_display_name_falls_back_to_basename() -> None:
    m = ExperimentArtifactsMapper()
    assert m.display_name_for_tracked("group/sub/file.txt", {}) == "file.txt"


def test_tracked_upload_to_dto_prefers_upload_filename() -> None:
    m = ExperimentArtifactsMapper()
    experiment_id = uuid4()
    row_id = uuid4()
    item = ExperimentTrackedUploadResponseDTO(
        id=row_id,
        hash="cd" * 32,
        file_path="weights/epoch-2.pt",
        mime_type="application/octet-stream",
        size=20,
        metadata={"name": "weights"},
    )
    dto = m.tracked_upload_to_dto(experiment_id, item, "custom.pt")
    assert dto.filename == "custom.pt"
    assert dto.name == "weights"
    assert dto.filepath == "weights/epoch-2.pt"
