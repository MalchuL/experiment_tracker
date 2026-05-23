"""DTO validation for snapshot manifest entries."""

import pytest
from pydantic import ValidationError

from object_storage.domain.project_artifacts_storage.dto import SnapshotFileEntryDTO


def test_snapshot_file_entry_accepts_path_at_1024() -> None:
    path = "x" * 1024
    row = SnapshotFileEntryDTO(path=path, hash="a" * 64)
    assert len(row.path) == 1024


def test_snapshot_file_entry_rejects_path_over_1024() -> None:
    with pytest.raises(ValidationError):
        SnapshotFileEntryDTO(path="z" * 1025, hash="b" * 64)
