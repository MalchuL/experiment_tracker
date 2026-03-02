from __future__ import annotations

from typing import Iterable, Protocol
from uuid import UUID

from .dto import ArtifactsInfoResultDTO, LogArtifactRequestDTO, LogArtifactResponseDTO


class ArtifactsInfoClientProtocol(Protocol):
    async def log_artifact(
        self, project_id: UUID, experiment_id: UUID, payload: LogArtifactRequestDTO
    ) -> LogArtifactResponseDTO: ...

    async def get_artifacts(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        artifact_types: Iterable[str] | None = None,
        artifact_names: Iterable[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO: ...

