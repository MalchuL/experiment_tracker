"""Map object-storage tracked payloads and path rules to domain DTOs."""

from __future__ import annotations

import os
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from clients.object_storage import (
    ExperimentTrackedArtifactInfoDTO,
    ExperimentTrackedArtifactItemDTO,
    ExperimentTrackedUploadResponseDTO,
)

from .dto import ExperimentArtifactDTO
from experiment_tracker_shared import utc_now_naive


class ExperimentArtifactsMapper:
    """Path normalization and DTO mapping for experiment-scoped tracked artifacts."""

    def validate_artifact_name(self, name: str) -> str:
        """Validate logical artifact name (single segment, safe)."""

        stripped = name.strip()
        normalized = stripped.replace("\\", "/")
        pure = PurePosixPath(normalized)
        if (
            not stripped
            or "/" in normalized
            or ".." in pure.parts
            or any(":" in p for p in pure.parts)
        ):
            raise ValueError(
                "Invalid artifact name: must be non-empty, single path segment, "
                "no '..', '/', or ':'."
            )
        return stripped

    def normalize_relative_filepath(self, filepath: str) -> str:
        """Validate a relative path under a logical artifact name."""

        normalized = filepath.strip().replace("\\", "/")
        pure_path = PurePosixPath(normalized)
        if (
            not normalized
            or normalized.startswith("/")
            or ".." in pure_path.parts
            or ":" in normalized
        ):
            raise ValueError(
                "Invalid filepath. It must be relative, non-empty, "
                "must not contain '..', ':' or start with '/'."
            )
        return normalized

    def display_name_for_tracked(
        self, file_path: str, metadata: dict[str, Any] | None
    ) -> str:
        """Prefer ``metadata['name']``; else basename of ``file_path``."""

        md = metadata or {}
        raw = md.get("name")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        norm = file_path.strip().replace("\\", "/")
        base = os.path.basename(norm)
        if base:
            return base
        return "artifact"

    def tracked_item_to_dto(
        self, experiment_id: UUID, item: ExperimentTrackedArtifactItemDTO
    ) -> ExperimentArtifactDTO:
        """Map a listed tracked row from object storage to :class:`ExperimentArtifactDTO`."""

        md = item.metadata or {}
        now = utc_now_naive()
        display_name = self.display_name_for_tracked(item.file_path, md)
        filename = os.path.basename(item.file_path) or display_name
        return ExperimentArtifactDTO(
            id=item.id,
            experiment_id=experiment_id,
            name=display_name,
            filepath=item.file_path,
            filename=filename,
            mime_type=item.mime_type,
            storage_path=item.hash,
            metadata=md,
            created_at=now,
            updated_at=now,
        )

    def tracked_upload_to_dto(
        self,
        experiment_id: UUID,
        item: ExperimentTrackedUploadResponseDTO,
        upload_filename: str | None,
    ) -> ExperimentArtifactDTO:
        """Map a tracked upload response to :class:`ExperimentArtifactDTO`."""

        md = item.metadata or {}
        now = utc_now_naive()
        filename = upload_filename or os.path.basename(item.file_path) or "artifact"
        display_name = self.display_name_for_tracked(item.file_path, md)
        return ExperimentArtifactDTO(
            id=item.id,
            experiment_id=experiment_id,
            name=display_name,
            filepath=item.file_path,
            filename=filename,
            mime_type=item.mime_type,
            storage_path=item.hash,
            metadata=md,
            created_at=now,
            updated_at=now,
        )

    def tracked_info_to_dto(
        self, experiment_id: UUID, item: ExperimentTrackedArtifactInfoDTO
    ) -> ExperimentArtifactDTO:
        md = item.metadata or {}
        display_name = self.display_name_for_tracked(item.file_path, md)
        filename = os.path.basename(item.file_path) or display_name
        return ExperimentArtifactDTO(
            id=item.id,
            experiment_id=experiment_id,
            name=display_name,
            filepath=item.file_path,
            filename=filename,
            mime_type=item.mime_type,
            storage_path=item.hash,
            metadata=md,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
