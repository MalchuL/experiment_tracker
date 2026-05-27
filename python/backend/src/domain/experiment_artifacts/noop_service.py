"""No-op experiment artifacts service when object storage is disabled."""

from __future__ import annotations

from uuid import UUID

from fastapi import UploadFile
from fastapi_users.models import UserProtocol

from clients.artifacts_info import (
    ArtifactType,
    ArtifactsInfoResultDTO,
    ArtifactsInfoSummaryResultDTO,
    LogArtifactResponseDTO as ArtifactsInfoLogArtifactResponseDTO,
)
from clients.object_storage import (
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
)
from lib.pagination import ListOptions

from .dto import (
    ExperimentArtifactDownloadDTO,
    ExperimentArtifactDTO,
    ExperimentArtifactListResponseDTO,
)
from .error import ExperimentArtifactsNotAccessibleError


class NoOpExperimentArtifactsService:
    """Fallback experiment-artifacts service used when object storage is disabled.

    List/query methods return empty DTOs and byte-producing methods raise
    ``ExperimentArtifactsNotAccessibleError`` so callers get predictable behavior in
    test or reduced local environments.
    """

    async def list_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        list_options: ListOptions = ListOptions(),
        file_paths: list[str] | None = None,
    ) -> ExperimentArtifactListResponseDTO:
        """Return an empty tracked-artifact list.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            list_options: Ignored pagination options.
            file_paths: Ignored path filter.

        Returns:
            ExperimentArtifactListResponseDTO: Empty page.
        """
        return ExperimentArtifactListResponseDTO(
            data=[],
            has_next=False,
            size=0,
            total=0,
        )

    async def get_experiments_artifacts_at_step(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        artifact_types: list[ArtifactType] | None = None,
        artifact_names: list[str] | None = None,
        steps: list[int] | None = None,
        list_options: ListOptions = ListOptions(),
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        """Return an empty at-step artifact query result.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            experiment_ids: Ignored experiment filter.
            artifact_types: Ignored type filter.
            artifact_names: Ignored name filter.
            steps: Ignored step filter.
            list_options: Ignored pagination options.
            start_time: Ignored lower timestamp bound.
            end_time: Ignored upper timestamp bound.

        Returns:
            ArtifactsInfoResultDTO: Empty page.
        """
        return ArtifactsInfoResultDTO(data=[], has_next=False, size=0, total=0)

    async def get_experiments_artifacts_summary_at_step(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        artifact_types: list[ArtifactType] | None = None,
        artifact_names: list[str] | None = None,
        list_options: ListOptions = ListOptions(),
        max_steps: int | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoSummaryResultDTO:
        """Return an empty at-step artifact summary result.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            experiment_ids: Ignored experiment filter.
            artifact_types: Ignored type filter.
            artifact_names: Ignored name filter.
            list_options: Ignored pagination options.
            max_steps: Ignored per-artifact step cap.
            start_time: Ignored lower timestamp bound.
            end_time: Ignored upper timestamp bound.

        Returns:
            ArtifactsInfoSummaryResultDTO: Empty page.
        """
        return ArtifactsInfoSummaryResultDTO(data=[], has_next=False, size=0, total=0)

    async def get_experiment_artifact_detail_at_step(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_id: UUID,
        artifact_name: str,
        step: int,
        artifact_type: ArtifactType | None = None,
    ) -> ArtifactsInfoResultDTO:
        """Return an empty at-step artifact detail result.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            experiment_id: Ignored experiment id.
            artifact_name: Ignored artifact name.
            step: Ignored step.
            artifact_type: Ignored artifact type.

        Returns:
            ArtifactsInfoResultDTO: Empty page.
        """
        return ArtifactsInfoResultDTO(data=[], has_next=False, size=0, total=0)

    async def upload_and_log_experiment_artifact_at_step(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        file: UploadFile,
        name: str,
        artifact_type: ArtifactType,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> ArtifactsInfoLogArtifactResponseDTO:
        """Return a benign no-op at-step logging result.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            file: Ignored upload stream.
            name: Ignored artifact name.
            artifact_type: Ignored artifact type.
            step: Ignored training step.
            metadata: Ignored metadata.
            tags: Ignored tags.

        Returns:
            ArtifactsInfoLogArtifactResponseDTO: Benign logged status.
        """
        return ArtifactsInfoLogArtifactResponseDTO(status="logged")

    async def download_experiment_artifact_at_step(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        step: int,
        name: str,
        artifact_type: ArtifactType | None = None,
    ) -> ExperimentArtifactDownloadDTO:
        """Reject at-step downloads when artifact storage is disabled.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            step: Ignored step.
            name: Ignored artifact name.
            artifact_type: Ignored artifact type.

        Raises:
            ExperimentArtifactsNotAccessibleError: Always raised because bytes are
                unavailable without object storage.

        Returns:
            Never returns successfully.
        """
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def delete_experiment_artifact_by_hash(
        self, user: UserProtocol, experiment_id: UUID, hash: str
    ) -> DeleteExperimentArtifactResponseDTO:
        """Return a successful no-op artifact deletion result.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            hash: Ignored artifact hash.

        Returns:
            DeleteExperimentArtifactResponseDTO: Benign deletion status.
        """
        return DeleteExperimentArtifactResponseDTO(deleted=True)

    async def delete_experiment_all_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        """Return a successful no-op all-artifacts deletion result.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.

        Returns:
            DeleteExperimentArtifactsResponseDTO: Zero deleted artifacts.
        """
        return DeleteExperimentArtifactsResponseDTO(deleted_count=0)

    async def delete_experiment_tracked_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        *,
        filepath: str,
    ) -> DeleteExperimentArtifactResponseDTO:
        """Return a successful no-op tracked-artifact deletion result.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            filepath: Ignored tracked artifact path.

        Returns:
            DeleteExperimentArtifactResponseDTO: Benign deletion status.
        """
        return DeleteExperimentArtifactResponseDTO(deleted=True)

    async def upsert_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str | None,
        filepath: str,
        file: UploadFile,
    ) -> ExperimentArtifactDTO:
        """Reject tracked-artifact upserts when storage is disabled.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            name: Ignored display name.
            filepath: Ignored artifact path.
            file: Ignored upload stream.

        Raises:
            ExperimentArtifactsNotAccessibleError: Always raised because storage is
                unavailable.

        Returns:
            Never returns successfully.
        """
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def get_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentArtifactDTO:
        """Reject tracked-artifact metadata reads when storage is disabled.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            filepath: Ignored path identifier.
            blob_id: Ignored blob identifier.
            artifact_hash: Ignored hash identifier.

        Raises:
            ExperimentArtifactsNotAccessibleError: Always raised because storage is
                unavailable.

        Returns:
            Never returns successfully.
        """
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def download_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentArtifactDownloadDTO:
        """Reject tracked-artifact downloads when storage is disabled.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            filepath: Ignored path identifier.
            blob_id: Ignored blob identifier.
            artifact_hash: Ignored hash identifier.

        Raises:
            ExperimentArtifactsNotAccessibleError: Always raised because bytes are
                unavailable without object storage.

        Returns:
            Never returns successfully.
        """
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def download_experiment_artifacts_archive(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
    ) -> tuple[str, str]:
        """Reject tracked-artifact archive downloads when storage is disabled.

        Args:
            user: Ignored user context.
            experiment_id: Ignored experiment id.
            name: Ignored artifact display name.

        Raises:
            ExperimentArtifactsNotAccessibleError: Always raised because archive bytes
                are unavailable without object storage.

        Returns:
            Never returns successfully.
        """
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")
