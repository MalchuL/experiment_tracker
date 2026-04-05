from __future__ import annotations

from typing import Iterable, Protocol
from uuid import UUID

from .dto import ArtifactsInfoResultDTO, LogArtifactRequestDTO, LogArtifactResponseDTO


class ArtifactsInfoClientProtocol(Protocol):
    async def log_artifact_at_step(
        self, project_id: UUID, experiment_id: UUID, payload: LogArtifactRequestDTO
    ) -> LogArtifactResponseDTO:
        """Log an artifact info to the scalars_service.

        Args:
            project_id: The ID of the project.
            experiment_id: The ID of the experiment (that under project).
            payload: The payload to log.

        Returns:
            The response from the scalars_service.
        """

    async def get_artifacts(
        self,
        project_id: UUID,
        experiment_ids: Iterable[UUID] | None = None,
        artifact_types: Iterable[str] | None = None,
        artifact_names: Iterable[str] | None = None,
        steps: Iterable[int] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        """Get artifacts info from the scalars_service.

        Args:
            project_id: The ID of the project.
            experiment_ids: The IDs of the experiments (that under project).
            artifact_types: The types of the artifacts.
            artifact_names: The names of the artifacts.
            steps: Training step indices to filter by.
            start_time: The start time of the artifacts.
            end_time: The end time of the artifacts.

        Returns:
            ArtifactsInfoResultDTO: The response from the scalars_service.
        """
