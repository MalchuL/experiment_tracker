"""Map experiment-data rows and snapshot payloads to domain/client DTOs."""

from __future__ import annotations

from uuid import UUID

from clients.object_storage import (
    SnapshotCreateRequestDTO as StorageSnapshotCreateRequestDTO,
)
from clients.object_storage import SnapshotFileEntryDTO as StorageSnapshotFileEntryDTO
from lib.types import UUID_TYPE
from models import ExperimentData

from .dto import ExperimentHparamsDTO, ExperimentSnapshotDTO, SnapshotFileEntryDTO


class ExperimentDataMapper:
    """DTO mapping helpers for experiment-scoped data records."""

    def snapshot_create_request(
        self,
        *,
        project_id: UUID_TYPE,
        experiment_id: UUID_TYPE,
        files: list[SnapshotFileEntryDTO],
    ) -> StorageSnapshotCreateRequestDTO:
        """Map public snapshot file entries to object-storage create payload."""

        return StorageSnapshotCreateRequestDTO(
            project_id=project_id,
            experiment_id=experiment_id,
            files=[
                StorageSnapshotFileEntryDTO(
                    path=item.path,
                    hash=item.hash,
                    size=item.size,
                )
                for item in files
            ],
        )

    def snapshot_to_dto(
        self, experiment_id: UUID, row: ExperimentData | None
    ) -> ExperimentSnapshotDTO:
        """Map a snapshot metadata row to the public API DTO."""

        return ExperimentSnapshotDTO(
            experiment_id=experiment_id,
            snapshot_id=self.snapshot_id_from_data(row),
            data_id=row.id if row else None,
            created_at=row.created_at if row else None,
            updated_at=row.updated_at if row else None,
        )

    def snapshot_id_from_data(self, row: ExperimentData | None) -> UUID | None:
        """Extract a snapshot UUID from an experiment-data metadata row."""

        if row is None:
            return None
        raw = row.data.get("snapshot_id") if isinstance(row.data, dict) else None
        if not raw:
            return None
        return UUID(str(raw))

    def hparams_to_dto(
        self, experiment_id: UUID, row: ExperimentData | None
    ) -> ExperimentHparamsDTO:
        """Map the current hparams row, preserving an explicit missing document."""

        return ExperimentHparamsDTO(
            experiment_id=experiment_id,
            hparams=row.data if row else None,
            data_id=row.id if row else None,
            created_at=row.created_at if row else None,
            updated_at=row.updated_at if row else None,
        )
