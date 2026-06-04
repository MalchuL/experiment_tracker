from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath
from uuid import UUID

import httpx
from domain.experiments.repository import ExperimentRepository
from domain.project_artifacts.protocol import ProjectArtifactsServiceProtocol
from lib.logger import get_logger
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from models import Experiment, ExperimentData, ExperimentDataType

from .dto import (
    ExperimentSnapshotDTO,
    ExperimentSnapshotFileContentDTO,
    ExperimentSnapshotFilesDTO,
    SnapshotFileManifestEntryDTO,
    SnapshotFileEntryDTO,
)
from .error import ExperimentSnapshotNotFoundError
from .mapper import ExperimentDataMapper
from .repository import ExperimentDataRepository

logger = get_logger(__name__)

class ExperimentDataService:
    """Coordinate snapshot DB metadata and project-artifact snapshot operations.

    Args:
        experiment_repository: Repository used to load experiment ownership.
        experiment_data_repository: Repository used for snapshot metadata rows.
        project_artifacts_service: Domain service for snapshot/CAS operations.

    Result:
        A service object exposing snapshot metadata, manifest listing, lazy file
        content, and delete workflows for API routes.
    """

    def __init__(
        self,
        experiment_repository: ExperimentRepository,
        experiment_data_repository: ExperimentDataRepository,
        project_artifacts_service: ProjectArtifactsServiceProtocol,
    ) -> None:
        """Store collaborators required by snapshot workflows.

        Args:
            experiment_repository: Experiment lookup repository.
            experiment_data_repository: Experiment-data metadata repository.
            project_artifacts_service: Domain service for CAS and snapshot
                storage operations.

        Returns:
            None.
        """
        self._experiments = experiment_repository
        self._data = experiment_data_repository
        self._project_artifacts = project_artifacts_service
        self._mapper = ExperimentDataMapper()

    async def _get_experiment_for_log(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> Experiment:
        """Load an experiment and verify the user may log artifact data.

        Args:
            user: Authenticated user requesting a snapshot write operation.
            experiment_id: Experiment to load and authorize.

        Returns:
            The loaded experiment when artifact logging is allowed.
        """
        experiment = await self._experiments.get_by_id(experiment_id)
        await self._project_artifacts.ensure_log_project_artifacts(
            user, experiment.project_id
        )
        return experiment

    async def _get_experiment_for_view(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> Experiment:
        """Load an experiment and verify the user may view artifact data.

        Args:
            user: Authenticated user requesting a snapshot read operation.
            experiment_id: Experiment to load and authorize.

        Returns:
            The loaded experiment when artifact viewing is allowed.
        """
        experiment = await self._experiments.get_by_id(experiment_id)
        await self._project_artifacts.ensure_view_project_artifacts(
            user, experiment.project_id
        )
        return experiment

    async def upsert_snapshot(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        files: list[SnapshotFileEntryDTO],
    ) -> ExperimentSnapshotDTO:
        """Create or replace the snapshot manifest for an experiment.

        Args:
            user: Authenticated user performing the write.
            experiment_id: Experiment whose snapshot should be replaced.
            files: Complete snapshot manifest of relative paths and hashes.

        Returns:
            Public snapshot metadata for the new archive.
        """
        experiment = await self._get_experiment_for_log(user, experiment_id)
        existing = await self._data.get_by_experiment_and_type(
            experiment_id, ExperimentDataType.SNAPSHOT
        )
        old_snapshot_id = self._mapper.snapshot_id_from_data(existing)

        storage_payload = self._mapper.snapshot_create_request(
            project_id=experiment.project_id,
            experiment_id=experiment.id,
            files=files,
        )
        created = await self._project_artifacts.create_project_snapshot(
            user, experiment.project_id, storage_payload
        )
        new_snapshot_id = UUID(created.snapshot_id)
        try:
            if existing is None:
                row = ExperimentData(
                    experiment_id=experiment_id,
                    type=ExperimentDataType.SNAPSHOT,
                    data={"snapshot_id": str(new_snapshot_id)},
                )
                await self._data.create(row)
            else:
                row = await self._data.update(
                    existing.id,
                    data={"snapshot_id": str(new_snapshot_id)},
                )
            await self._data.commit()
        except Exception:
            await self._data.rollback()
            try:
                await self._project_artifacts.delete_project_snapshot(
                    user, experiment.project_id, new_snapshot_id
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Failed to delete orphaned snapshot %s after DB rollback",
                    new_snapshot_id,
                )
            raise

        if old_snapshot_id and old_snapshot_id != new_snapshot_id:
            try:
                await self._project_artifacts.delete_project_snapshot(
                    user, experiment.project_id, old_snapshot_id
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Failed to delete replaced snapshot %s", old_snapshot_id
                )

        return self._mapper.snapshot_to_dto(experiment_id, row)

    async def list_snapshots(
        self, user: UserProtocol, experiment_ids: Sequence[UUID]
    ) -> list[ExperimentSnapshotDTO]:
        """List snapshot metadata for several experiments after authorization.

        Args:
            user: Authenticated user performing the read.
            experiment_ids: Experiments to resolve, preserving caller order.

        Returns:
            One ``ExperimentSnapshotDTO`` per requested experiment. Entries with
            no metadata row have ``snapshot_id=None``.
        """
        experiments_by_id: dict[UUID, Experiment] = {}
        for experiment_id in experiment_ids:
            experiment = await self._get_experiment_for_view(user, experiment_id)
            experiments_by_id[experiment.id] = experiment
        rows = await self._data.list_by_experiments_and_type(
            list(experiments_by_id), ExperimentDataType.SNAPSHOT
        )
        rows_by_experiment = {row.experiment_id: row for row in rows}
        return [
            self._mapper.snapshot_to_dto(
                experiment_id, rows_by_experiment.get(experiment_id)
            )
            for experiment_id in experiment_ids
        ]

    async def get_snapshot_files(
        self, user: UserProtocol, experiment_ids: Sequence[UUID]
    ) -> list[ExperimentSnapshotFilesDTO]:
        """Return snapshot manifests without downloading file contents.

        Args:
            user: Authenticated user performing the read.
            experiment_ids: Experiments whose snapshots should be inspected.

        Returns:
            Per-experiment manifest payloads. Missing snapshots produce empty
            file lists with ``snapshot_id=None``.
        """
        result: list[ExperimentSnapshotFilesDTO] = []
        for experiment_id in experiment_ids:
            experiment = await self._get_experiment_for_view(user, experiment_id)
            row = await self._data.get_by_experiment_and_type(
                experiment_id, ExperimentDataType.SNAPSHOT
            )
            snapshot_id = self._mapper.snapshot_id_from_data(row)
            if snapshot_id is None:
                result.append(
                    ExperimentSnapshotFilesDTO(
                        experiment_id=experiment_id,
                        snapshot_id=None,
                        files=[],
                    )
                )
                continue

            result.append(
                await self._snapshot_files_from_snapshot_id(
                    user=user,
                    experiment=experiment,
                    snapshot_id=snapshot_id,
                )
            )
        return result

    async def get_experiment_snapshot_files(
        self, user: UserProtocol, experiment_id: UUID
    ) -> ExperimentSnapshotFilesDTO:
        """Return one experiment snapshot manifest without downloading file contents."""

        experiment = await self._get_experiment_for_view(user, experiment_id)
        row = await self._data.get_by_experiment_and_type(
            experiment_id, ExperimentDataType.SNAPSHOT
        )
        snapshot_id = self._mapper.snapshot_id_from_data(row)
        if snapshot_id is None:
            return ExperimentSnapshotFilesDTO(
                experiment_id=experiment_id,
                snapshot_id=None,
                files=[],
            )
        return await self._snapshot_files_from_snapshot_id(
            user=user,
            experiment=experiment,
            snapshot_id=snapshot_id,
        )

    async def get_snapshot_file_content(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        path: str,
        file_hash: str,
    ) -> ExperimentSnapshotFileContentDTO:
        """Load one snapshot file after validating it belongs to the manifest.

        Args:
            user: Authenticated user performing the read.
            experiment_id: Experiment whose snapshot file should be fetched.
            path: Relative file path from the current snapshot manifest.
            file_hash: SHA-256 hash expected for the file.

        Returns:
            UTF-8 file content for the requested manifest entry.
        """
        experiment = await self._get_experiment_for_view(user, experiment_id)
        row = await self._data.get_by_experiment_and_type(
            experiment_id, ExperimentDataType.SNAPSHOT
        )
        snapshot_id = self._mapper.snapshot_id_from_data(row)
        if snapshot_id is None:
            raise ExperimentSnapshotNotFoundError(
                f"No snapshot found for experiment {experiment_id}"
            )
        return await self._get_snapshot_file_content_for_snapshot(
            user=user,
            experiment=experiment,
            snapshot_id=snapshot_id,
            path=path,
            file_hash=file_hash,
        )

    async def get_snapshot_file_content_for_snapshot(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        snapshot_id: UUID,
        path: str,
        file_hash: str,
    ) -> ExperimentSnapshotFileContentDTO:
        """Load one file from the experiment's current snapshot by exact snapshot id."""

        experiment = await self._get_experiment_for_view(user, experiment_id)
        row = await self._data.get_by_experiment_and_type(
            experiment_id, ExperimentDataType.SNAPSHOT
        )
        current_snapshot_id = self._mapper.snapshot_id_from_data(row)
        if current_snapshot_id is None or current_snapshot_id != snapshot_id:
            raise ExperimentSnapshotNotFoundError(
                f"No matching snapshot found for experiment {experiment_id}"
            )
        return await self._get_snapshot_file_content_for_snapshot(
            user=user,
            experiment=experiment,
            snapshot_id=snapshot_id,
            path=path,
            file_hash=file_hash,
        )

    async def download_snapshot(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        *,
        snapshot_id: UUID | None = None,
    ) -> httpx.Response:
        """Download a snapshot ZIP for an experiment.

        When ``snapshot_id`` is omitted, resolves the ID from experiment snapshot metadata.
        When provided, downloads that snapshot directly without a current-snapshot check.
        """

        experiment = await self._get_experiment_for_view(user, experiment_id)
        if snapshot_id is not None:
            resolved_snapshot_id = snapshot_id
        else:
            row = await self._data.get_by_experiment_and_type(
                experiment_id, ExperimentDataType.SNAPSHOT
            )
            resolved_snapshot_id = self._mapper.snapshot_id_from_data(row)
            if resolved_snapshot_id is None:
                raise ExperimentSnapshotNotFoundError(
                    f"No snapshot found for experiment {experiment_id}"
                )
        return await self._project_artifacts.download_project_snapshot(
            user, experiment.project_id, resolved_snapshot_id
        )

    async def delete_snapshot(
        self, user: UserProtocol, experiment_id: UUID
    ) -> ExperimentSnapshotDTO:
        """Delete an experiment snapshot from storage and metadata tables.

        Args:
            user: Authenticated user performing the delete.
            experiment_id: Experiment whose snapshot should be removed.

        Returns:
            Snapshot DTO for the experiment after deletion, with no snapshot ID.
        """
        experiment = await self._get_experiment_for_log(user, experiment_id)
        row = await self._data.get_by_experiment_and_type(
            experiment_id, ExperimentDataType.SNAPSHOT
        )
        snapshot_id = self._mapper.snapshot_id_from_data(row)
        if snapshot_id is None:
            raise ExperimentSnapshotNotFoundError(
                f"No snapshot found for experiment {experiment_id}"
            )

        await self._project_artifacts.delete_project_snapshot(
            user, experiment.project_id, snapshot_id
        )
        try:
            await self._data.delete_by_experiment_and_type(
                experiment_id, ExperimentDataType.SNAPSHOT
            )
            await self._data.commit()
        except Exception:
            await self._data.rollback()
            raise

        return self._mapper.snapshot_to_dto(experiment_id, None)

    def _is_safe_relative_path(self, path: str) -> bool:
        """Check whether an archive path is safe to expose as relative content.

        Args:
            path: POSIX path from a ZIP member.

        Returns:
            ``True`` when the path is relative and contains no parent-directory
            traversal components; otherwise ``False``.
        """
        pure = PurePosixPath(path)
        return not pure.is_absolute() and ".." not in pure.parts

    async def _snapshot_files_from_snapshot_id(
        self,
        *,
        user: UserProtocol,
        experiment: Experiment,
        snapshot_id: UUID,
    ) -> ExperimentSnapshotFilesDTO:
        """Map a storage manifest to the public experiment snapshot-files DTO."""

        manifest = await self._project_artifacts.get_project_snapshot_manifest(
            user, experiment.project_id, snapshot_id
        )
        return ExperimentSnapshotFilesDTO(
            experiment_id=experiment.id,
            snapshot_id=snapshot_id,
            files=[
                SnapshotFileManifestEntryDTO(
                    path=file.path,
                    hash=file.hash,
                    size=file.size,
                )
                for file in manifest.files
            ],
        )

    async def _get_snapshot_file_content_for_snapshot(
        self,
        *,
        user: UserProtocol,
        experiment: Experiment,
        snapshot_id: UUID,
        path: str,
        file_hash: str,
    ) -> ExperimentSnapshotFileContentDTO:
        """Validate manifest identity and return UTF-8 file content."""

        requested_path = path.strip().replace("\\", "/")
        requested_hash = file_hash.strip().lower()
        if not self._is_safe_relative_path(requested_path):
            raise ExperimentSnapshotNotFoundError(
                f"Snapshot file not found for experiment {experiment.id}"
            )

        manifest = await self._project_artifacts.get_project_snapshot_manifest(
            user, experiment.project_id, snapshot_id
        )
        match = next(
            (
                file
                for file in manifest.files
                if file.path == requested_path and file.hash.lower() == requested_hash
            ),
            None,
        )
        if match is None:
            raise ExperimentSnapshotNotFoundError(
                f"Snapshot file not found for experiment {experiment.id}"
            )

        raw = await self._project_artifacts.download_project_artifact(
            user, experiment.project_id, requested_hash
        )
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExperimentSnapshotNotFoundError(
                f"Snapshot file is not UTF-8 text: {requested_path}"
            ) from exc
        return ExperimentSnapshotFileContentDTO(
            path=match.path,
            hash=match.hash,
            content=content,
            size=len(raw),
        )
