from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath
from uuid import UUID

import httpx
from domain.experiments.repository import ExperimentRepository
from domain.project_artifacts.protocol import ProjectArtifactsServiceProtocol
from domain.rbac.wrapper import PermissionChecker
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
    ExperimentHparamsListItemDTO,
    ExperimentHparamsListResponseDTO,
    ExperimentHparamsDTO,
)
from .error import ExperimentDataNotAccessibleError, ExperimentSnapshotNotFoundError
from .mapper import ExperimentDataMapper
from .repository import ExperimentDataRepository

logger = get_logger(__name__)

class ExperimentDataService:
    """Orchestrate experiment code snapshots across Postgres and object storage.

    Purpose:
        Experiments store a lightweight ``ExperimentData`` row (type ``SNAPSHOT``)
        that points at a project-scoped snapshot archive in object storage. This
        service owns authorization, metadata CRUD, manifest reads, optional UTF-8
        file preview, ZIP download, and cleanup while delegating bytes to
        :class:`domain.project_artifacts` / CAS APIs.

    Collaborators:
        experiment_repository: Resolves ``project_id`` for RBAC and storage calls.
        experiment_data_repository: Persists which snapshot UUID is current per experiment.
        project_artifacts_service: Creates, lists, downloads, and deletes snapshot archives.
    """

    def __init__(
        self,
        experiment_repository: ExperimentRepository,
        experiment_data_repository: ExperimentDataRepository,
        project_artifacts_service: ProjectArtifactsServiceProtocol,
        permission_checker: PermissionChecker | None = None,
    ) -> None:
        """Wire repositories and the project-artifacts facade used by all snapshot flows."""
        self._experiments = experiment_repository
        self._data = experiment_data_repository
        self._project_artifacts = project_artifacts_service
        self._permissions = permission_checker
        self._mapper = ExperimentDataMapper()

    def _permission_checker(self) -> PermissionChecker:
        if self._permissions is None:
            raise RuntimeError("Experiment-data permission checker is not configured")
        return self._permissions

    async def _get_experiment_for_hparams_view(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> Experiment:
        experiment = await self._experiments.get_by_id(experiment_id)
        if not await self._permission_checker().can_view_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentDataNotAccessibleError(
                f"Experiment {experiment_id} is not accessible"
            )
        return experiment

    async def _get_experiment_for_hparams_edit(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> Experiment:
        experiment = await self._experiments.get_by_id(experiment_id)
        if not await self._permission_checker().can_edit_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentDataNotAccessibleError(
                f"Experiment {experiment_id} is not accessible"
            )
        return experiment

    async def get_hparams(
        self, user: UserProtocol, experiment_id: UUID
    ) -> ExperimentHparamsDTO:
        await self._get_experiment_for_hparams_view(user, experiment_id)
        row = await self._data.get_by_experiment_and_type(
            experiment_id, ExperimentDataType.HPARAMS
        )
        return self._mapper.hparams_to_dto(experiment_id, row)

    async def upsert_hparams(
        self, user: UserProtocol, experiment_id: UUID, hparams: dict[str, object]
    ) -> ExperimentHparamsDTO:
        await self._get_experiment_for_hparams_edit(user, experiment_id)
        row = await self._data.get_by_experiment_and_type(
            experiment_id, ExperimentDataType.HPARAMS
        )
        if row is None:
            row = ExperimentData(
                experiment_id=experiment_id,
                type=ExperimentDataType.HPARAMS,
                data=hparams,
            )
            await self._data.create(row)
        else:
            row = await self._data.update(row.id, data=hparams)
        await self._data.commit()
        return self._mapper.hparams_to_dto(experiment_id, row)

    async def delete_hparams(
        self, user: UserProtocol, experiment_id: UUID
    ) -> ExperimentHparamsDTO:
        await self._get_experiment_for_hparams_edit(user, experiment_id)
        await self._data.delete_by_experiment_and_type(
            experiment_id, ExperimentDataType.HPARAMS
        )
        await self._data.commit()
        return self._mapper.hparams_to_dto(experiment_id, None)

    async def list_hparams(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID],
    ) -> ExperimentHparamsListResponseDTO:
        if not await self._permission_checker().can_view_experiment(user.id, project_id):
            raise ExperimentDataNotAccessibleError(
                f"Project {project_id} is not accessible"
            )
        unique_ids = list(dict.fromkeys(experiment_ids))
        experiments = await self._experiments.get_experiments_by_ids(
            unique_ids, include_features=False
        )
        by_id = {row.id: row for row in experiments if row.project_id == project_id}
        if len(by_id) != len(unique_ids):
            raise ExperimentDataNotAccessibleError(
                "One or more experiments do not belong to the requested project"
            )
        data_rows = await self._data.list_by_experiments_and_type(
            unique_ids, ExperimentDataType.HPARAMS
        )
        data_by_experiment = {row.experiment_id: row.data for row in data_rows}
        return ExperimentHparamsListResponseDTO(
            project_id=project_id,
            experiments=[
                ExperimentHparamsListItemDTO(
                    experiment_id=experiment_id,
                    experiment_name=by_id[experiment_id].name,
                    hparams=data_by_experiment.get(experiment_id),
                )
                for experiment_id in experiment_ids
            ],
        )

    async def _get_experiment_for_log(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> Experiment:
        """Authorize snapshot writes (upsert/delete) for the experiment's project.

        Purpose:
            Snapshot mutations require ``LOG_ARTIFACT``-equivalent access on the
            parent project before touching object storage or metadata rows.

        Args:
            user: Caller performing a write.
            experiment_id: Target experiment.

        Returns:
            The experiment row after project-level log permission succeeds.

        Raises:
            Domain/storage errors from the experiment or project-artifacts layers.
        """
        experiment = await self._experiments.get_by_id(experiment_id)
        await self._project_artifacts.ensure_log_project_artifacts(
            user, experiment.project_id
        )
        return experiment

    async def _get_experiment_for_view(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> Experiment:
        """Authorize snapshot reads (manifest, preview, download) for the experiment's project.

        Purpose:
            Read paths call ``ensure_view_project_artifacts`` so compare UI, SDK
            clients, and PATs with view scope cannot bypass project RBAC.

        Args:
            user: Caller performing a read.
            experiment_id: Target experiment.

        Returns:
            The experiment row after project-level view permission succeeds.

        Raises:
            Domain/storage errors from the experiment or project-artifacts layers.
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
        """Create or replace the code snapshot bound to one experiment.

        Purpose:
            Training jobs and the SDK upload files to project CAS first, then send
            a full manifest here. The service creates a new object-storage snapshot,
            updates (or inserts) the ``ExperimentData`` pointer, deletes the previous
            archive when replace succeeds, and rolls back storage if the DB commit fails.

        Args:
            user: Caller with log permission on the project.
            experiment_id: Experiment receiving the new snapshot pointer.
            files: Complete manifest (relative path + content hash per file).

        Returns:
            Public snapshot metadata including the new ``snapshot_id``.

        Raises:
            ExperimentSnapshotNotFoundError: Not used on upsert; storage/DB errors propagate.
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
        """Resolve snapshot IDs for many experiments without loading manifests.

        Purpose:
            Bulk compare and dashboard views need only ``snapshot_id`` (and row
            timestamps) per experiment, not per-file metadata. Order matches the
            caller's ``experiment_ids`` sequence.

        Args:
            user: Caller with view permission on each experiment's project.
            experiment_ids: Experiments to look up.

        Returns:
            One DTO per requested ID; missing rows use ``snapshot_id=None``.
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
        """Return per-file manifest entries for several experiments (metadata only).

        Purpose:
            Powers multi-experiment file-compare: list paths, hashes, and sizes so
            the UI can build trees and diff status without fetching blob bytes.

        Args:
            user: Caller with view permission on each experiment's project.
            experiment_ids: Experiments whose current snapshot manifests are needed.

        Returns:
            One ``ExperimentSnapshotFilesDTO`` per ID; absent snapshots yield empty
            ``files`` and ``snapshot_id=None``.
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
        """Return the current snapshot manifest for a single experiment.

        Purpose:
            Same as :meth:`get_snapshot_files` but for one experiment—used by the
            compare page when only the left or right side changes, avoiding a bulk POST.

        Args:
            user: Caller with view permission on the project.
            experiment_id: Experiment whose manifest should be listed.

        Returns:
            Manifest DTO; when no snapshot exists, ``snapshot_id`` is ``None`` and
            ``files`` is empty (no error).

        Raises:
            ExperimentDataNotAccessibleError: Propagated from authorization layers.
        """
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
        """Fetch UTF-8 text for one file in the experiment's *current* snapshot.

        Purpose:
            Server-side preview API for future clients that prefer a single
            experiment-data endpoint over direct project-artifact download. The
            caller must supply both ``path`` and ``hash`` so the service can confirm
            the file belongs to the logged manifest before returning decoded text.
            Compare UI today uses CAS download by hash instead; this route remains
            for API stability and non-browser consumers.

        Args:
            user: Caller with view permission on the project.
            experiment_id: Experiment whose *current* snapshot is read.
            path: Relative manifest path (e.g. ``src/train.py``).
            file_hash: Expected SHA-256 hex digest for that path.

        Returns:
            Path, hash, UTF-8 ``content``, and byte ``size`` after validation.

        Raises:
            ExperimentSnapshotNotFoundError: No snapshot, unknown path/hash, non-UTF-8,
                or unsafe path (absolute or ``..`` segments).
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

    async def download_snapshot(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        *,
        snapshot_id: UUID | None = None,
    ) -> httpx.Response:
        """Stream the snapshot archive ZIP from object storage.

        Purpose:
            Lets users download an experiment's code tree as one file (sidebar or
            compare). Without ``snapshot_id``, uses the pointer in ``ExperimentData``.
            With ``snapshot_id``, downloads that archive directly—useful when the UI
            already knows the manifest UUID (e.g. historical compare) without
            requiring it to match the current pointer.

        Args:
            user: Caller with view permission on the project.
            experiment_id: Experiment context for authorization and default resolution.
            snapshot_id: Optional explicit archive UUID; skips metadata lookup when set.

        Returns:
            Raw ``httpx.Response`` from object storage (ZIP body and headers).

        Raises:
            ExperimentSnapshotNotFoundError: No current snapshot when ``snapshot_id``
                is omitted and metadata has no pointer.
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
        """Remove the experiment's snapshot archive and metadata pointer.

        Purpose:
            Clears code snapshots when an experiment is reset or the user deletes
            logged files from the UI. Deletes the object-storage archive first, then
            the ``ExperimentData`` row; DB failures roll back without restoring storage.

        Args:
            user: Caller with log permission on the project.
            experiment_id: Experiment whose snapshot should be removed.

        Returns:
            Snapshot DTO with ``snapshot_id=None`` after successful deletion.

        Raises:
            ExperimentSnapshotNotFoundError: No snapshot pointer exists for the experiment.
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
        """Reject manifest paths that could escape the snapshot root (zip-slip style).

        Purpose:
            File-content preview only accepts relative, normalized paths without
            ``..`` or leading slashes so clients cannot probe arbitrary storage keys.

        Args:
            path: Manifest path after slash normalization.

        Returns:
            ``True`` when the path is safe to match against the manifest.
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
        """Load object-storage manifest rows into API file entries.

        Purpose:
            Shared helper for single- and multi-experiment manifest endpoints; keeps
            DTO mapping in one place after ``get_project_snapshot_manifest``.

        Args:
            user: Caller already authorized for the experiment's project.
            experiment: Experiment owning the snapshot pointer.
            snapshot_id: Object-storage snapshot UUID to read.

        Returns:
            ``ExperimentSnapshotFilesDTO`` with path/hash/size per manifest file.
        """
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
        """Resolve one manifest row to decoded UTF-8 text via project CAS.

        Purpose:
            Internal implementation for :meth:`get_snapshot_file_content`: confirm
            ``path`` + ``hash`` exist on the given snapshot, download bytes by hash,
            and decode as UTF-8. Binary or mismatched entries surface as not-found.

        Args:
            user: Caller with view permission on the project.
            experiment: Experiment used for ``project_id`` and error context.
            snapshot_id: Snapshot archive containing the manifest.
            path: Relative file path requested by the client.
            file_hash: Expected content hash for that path.

        Returns:
            Validated ``ExperimentSnapshotFileContentDTO``.

        Raises:
            ExperimentSnapshotNotFoundError: Invalid path, hash mismatch, missing
                manifest entry, or non-UTF-8 payload.
        """
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
