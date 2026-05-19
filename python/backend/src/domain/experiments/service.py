from typing import List, Literal

from .error import ExperimentNotAccessibleError
from lib.category_cleanup_dto import (
    CategoryCleanupErrorEntryDTO,
    CategoryCleanupResponseDTO,
    CategoryCleanupResultEntryDTO,
)
from lib.pagination import ListOptions
from lib.protocols.user_protocol import UserProtocol
from lib.satellite_deletion import SatelliteCallResult, run_satellite
from lib.deletion_outcome import (
    append_postgres_deleted,
    append_satellite_step,
    finalize_deletion_outcome,
)
from lib.satellite_step_dto import satellite_step_from_result
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import ExperimentRepository
from .dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentDeleteResponseDTO,
    ExperimentListResponseDTO,
    ExperimentScalarsUsageDTO,
    ExperimentUpdateDTO,
    ExperimentUsageDTO,
    ExperimentUsageSnapshotsDTO,
    ExperimentUsageTotalDTO,
    UsageBytesCountDTO,
)
from .mapper import ExperimentMapper
from domain.rbac.wrapper import PermissionChecker
from clients.object_storage import ObjectStorageClientProtocol
from clients.scalars.dto import ScalarsExperimentUsageResponseDTO
from domain.scalars.service import NoOpScalarsService, ScalarsServiceProtocol

ExperimentCleanupCategory = Literal[
    "experimentArtifacts", "atStepArtifacts", "scalars"
]


class ExperimentService:
    """Application layer for experiments: Postgres rows plus scalars and object-storage side effects.

    Creates and updates experiments in the main database; for deletion and usage it
    coordinates the **scalars** and **object storage** clients (via ``run_satellite``)
    so training/UI flows stay consistent across services.
    """

    def __init__(
        self,
        db: AsyncSession,
        experiment_repository: ExperimentRepository,
        permission_checker: PermissionChecker,
        scalars_service: ScalarsServiceProtocol | None = None,
        object_storage_client: ObjectStorageClientProtocol | None = None,
    ):
        self.db = db
        self.experiment_repository = experiment_repository
        self.permission_checker = permission_checker
        self.scalars_service = scalars_service or NoOpScalarsService()
        self.object_storage_client = object_storage_client
        self.experiment_mapper = ExperimentMapper()

    async def get_recent_experiments(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(limit=10, offset=0),
        *,
        include_features: bool = True,
    ) -> ExperimentListResponseDTO:
        if not await self.permission_checker.can_view_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to view experiments in project {project_id}"
            )
        experiments_page = await self.experiment_repository.get_latest_experiments(
            project_id, list_options, include_features=include_features
        )
        return ExperimentListResponseDTO.from_page(
            experiments_page.map(
                lambda experiment: self.experiment_mapper.experiment_schema_to_list_item_dto(
                    experiment, include_features=include_features
                )
            )
        )

    async def get_experiment_if_accessible(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> ExperimentDTO | None:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        if not await self.permission_checker.can_view_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"Experiment {experiment_id} not accessible"
            )
        return self.experiment_mapper.experiment_schema_to_dto(experiment)

    async def create_experiment(
        self, user: UserProtocol, data: ExperimentCreateDTO
    ) -> ExperimentDTO:
        if not await self.permission_checker.can_create_experiment(
            user.id, data.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to create an experiment in project {data.project_id}"
            )
        if data.parent_experiment_id:
            parent_id = data.parent_experiment_id
            experiment = await self.experiment_repository.get_by_id(parent_id)
            if not experiment:
                raise ExperimentNotAccessibleError(
                    f"Parent experiment {parent_id} not found"
                )
            if experiment.project_id != data.project_id:
                raise ExperimentNotAccessibleError(
                    f"Parent experiment {parent_id} not in project {data.project_id}"
                )

        experiment = self.experiment_mapper.experiment_create_dto_to_schema(data)
        await self.experiment_repository.create(experiment)
        await self.db.commit()
        return self.experiment_mapper.experiment_schema_to_dto(experiment)

    async def update_experiment(
        self, user: UserProtocol, experiment_id: UUID_TYPE, data: ExperimentUpdateDTO
    ) -> ExperimentDTO:
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        if not await self.permission_checker.can_edit_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to edit experiment {experiment_id}"
            )
        updates = self.experiment_mapper.experiment_update_dto_to_update_dict(data)
        result = await self.experiment_repository.update(experiment_id, **updates)
        await self.db.commit()

        return self.experiment_mapper.experiment_schema_to_dto(result)

    async def delete_experiment(
        self,
        user: UserProtocol,
        experiment_id: UUID_TYPE,
        *,
        detailed: bool = False,
    ) -> ExperimentDeleteResponseDTO:
        """Delete the experiment row after best-effort satellite cleanup.

        Order of operations:
        1. Verify ``DELETE_EXPERIMENT`` (or equivalent) permission for the experiment's project.
        2. Call object storage to remove **all** blobs for this experiment (tracked, at-step,
           untracked as implemented by the storage service). Wrapped in ``run_satellite`` so
           a down storage service does not block Postgres deletion, but the response records
           success vs skipped vs error.
        3. Call scalars ``delete_experiment_data`` to remove ClickHouse rows across scalars,
           artifacts metadata, and last-logged tables for this experiment.
        4. Delete the experiment from Postgres and commit.

        Returns:
            Cleanup-shaped payload with per-step ``results`` / ``errors`` (object storage,
            scalars, Postgres row).
        """
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        if not await self.permission_checker.can_delete_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to delete experiment {experiment_id}"
            )
        project_id = experiment.project_id
        if self.object_storage_client is not None:
            os_raw = await run_satellite(
                self.object_storage_client.delete_all_experiment_artifacts(
                    project_id, experiment_id
                )
            )
        else:
            os_raw = SatelliteCallResult(ok=True, skipped=True)
        sc_raw = await run_satellite(
            self.scalars_service.delete_experiment_data(project_id, experiment_id)
        )
        os_dto = satellite_step_from_result(os_raw)
        sc_dto = satellite_step_from_result(sc_raw)
        results: list[CategoryCleanupResultEntryDTO] = []
        errors: list[CategoryCleanupErrorEntryDTO] = []
        append_satellite_step(results, errors, "experiment:objectStorage", os_dto)
        append_satellite_step(results, errors, "experiment:scalars", sc_dto)
        await self.experiment_repository.delete(experiment_id)
        await self.db.commit()
        append_postgres_deleted(
            results, category="postgres:experiment", entity_id=experiment_id
        )
        finalized = finalize_deletion_outcome(results, errors, detailed=detailed)
        return ExperimentDeleteResponseDTO.model_validate(finalized.model_dump())

    async def get_experiment_usage(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> ExperimentUsageDTO:
        """Aggregate approximate storage for one experiment across object storage and scalars.

        Object storage returns counts/bytes for named experiment artifacts and at-step
        artifacts when configured; failures are swallowed into empty blocks while scalars
        usage still applies. ClickHouse usage (rows/bytes) comes from the scalars satellite.

        ``snapshots`` is reserved for future snapshot attribution and is returned as unknown
        with zero bytes today.

        Raises:
            ExperimentNotAccessibleError: If the user cannot view the experiment's project.
        """
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        if not await self.permission_checker.can_view_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"Experiment {experiment_id} not accessible"
            )
        object_usage = None
        if self.object_storage_client is not None:
            ou_res = await run_satellite(
                self.object_storage_client.get_experiment_usage(
                    experiment.project_id, experiment_id
                )
            )
            if ou_res.ok and ou_res.detail is not None:
                object_usage = ou_res.detail

        scalar_usage: ScalarsExperimentUsageResponseDTO | None = None
        su_res = await run_satellite(
            self.scalars_service.get_experiment_usage(
                experiment.project_id, experiment_id
            )
        )
        if su_res.ok and isinstance(su_res.detail, ScalarsExperimentUsageResponseDTO):
            scalar_usage = su_res.detail

        if object_usage is None:
            experiment_artifacts = UsageBytesCountDTO()
            at_step_artifacts = UsageBytesCountDTO()
        else:
            experiment_artifacts = UsageBytesCountDTO(
                count=int(object_usage.experiment_artifacts.count or 0),
                bytes=int(object_usage.experiment_artifacts.bytes or 0),
            )
            at_step_artifacts = UsageBytesCountDTO(
                count=int(object_usage.at_step_artifacts.count or 0),
                bytes=int(object_usage.at_step_artifacts.bytes or 0),
            )
        snapshots = ExperimentUsageSnapshotsDTO(
            count=0, bytes=0, known=False,
        )
        scalars = ExperimentScalarsUsageDTO(
            rows=int(scalar_usage.rows if scalar_usage else 0),
            bytes=int(scalar_usage.bytes if scalar_usage else 0),
        )
        total_bytes = (
            experiment_artifacts.bytes
            + at_step_artifacts.bytes
            + snapshots.bytes
            + scalars.bytes
        )
        return ExperimentUsageDTO(
            experiment_id=str(experiment_id),
            project_id=str(experiment.project_id),
            experiment_artifacts=experiment_artifacts,
            at_step_artifacts=at_step_artifacts,
            snapshots=snapshots,
            scalars=scalars,
            total=ExperimentUsageTotalDTO(bytes=total_bytes),
        )

    async def cleanup_experiment_category(
        self,
        user: UserProtocol,
        experiment_id: UUID_TYPE,
        category: ExperimentCleanupCategory,
    ) -> CategoryCleanupResponseDTO:
        """Danger-zone **partial** cleanup: remove one storage slice without deleting Postgres.

        Categories (path segment ``category``):
            ``experimentArtifacts`` — tracked blobs only (metadata + listed hashes).
            ``atStepArtifacts`` — objects in the experiment bucket not referenced by tracked rows.
            ``scalars`` — ClickHouse row delete for this experiment only.

        The response bundles parallel ``results`` and ``errors`` lists so the UI can show
        partial success when one backend fails.

        Raises:
            ExperimentNotAccessibleError: Missing delete permission on the experiment.
            ValueError: Unknown ``category`` value.
        """
        experiment = await self.experiment_repository.get_by_id(experiment_id)
        if not await self.permission_checker.can_delete_experiment(
            user.id, experiment.project_id
        ):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to clean experiment {experiment_id}"
            )
        errors: list[CategoryCleanupErrorEntryDTO] = []
        results: list[CategoryCleanupResultEntryDTO] = []
        if category in {"experimentArtifacts", "atStepArtifacts"}:
            if self.object_storage_client is None:
                errors.append(
                    CategoryCleanupErrorEntryDTO(
                        category=category,
                        error="Object storage is not configured",
                    )
                )
            else:
                try:
                    if category == "experimentArtifacts":
                        response = (
                            await self.object_storage_client.delete_tracked_experiment_artifacts(
                                experiment.project_id, experiment_id
                            )
                        )
                    else:
                        response = (
                            await self.object_storage_client.delete_untracked_experiment_blobs(
                                experiment.project_id, experiment_id
                            )
                        )
                    results.append(
                        CategoryCleanupResultEntryDTO(
                            category=category,
                            result=response.model_dump(),
                        )
                    )
                except Exception as exc:
                    errors.append(
                        CategoryCleanupErrorEntryDTO(
                            category=category,
                            error=str(exc),
                        )
                    )
        elif category == "scalars":
            try:
                res = await self.scalars_service.delete_experiment_data(
                    experiment.project_id, experiment_id
                )
                results.append(
                    CategoryCleanupResultEntryDTO(
                        category=category,
                        result=res.model_dump(mode="json", by_alias=True),
                    )
                )
            except Exception as exc:
                errors.append(
                    CategoryCleanupErrorEntryDTO(category=category, error=str(exc))
                )
        else:
            raise ValueError(f"Unknown cleanup category: {category}")
        return CategoryCleanupResponseDTO(
            success=not errors,
            partial=bool(results and errors),
            result_count=len(results),
            results=results,
            errors=errors,
        )

    async def reorder_experiments(
        self, user: UserProtocol, project_id: UUID_TYPE, data: List[UUID_TYPE]
    ) -> bool:
        if not await self.permission_checker.can_edit_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to edit experiments in project {project_id}"
            )
        experiments = (
            await self.experiment_repository.get_experiments_by_project(project_id)
        ).data
        for i, experiment_id in enumerate(data):
            experiment = next(
                (e for e in experiments if str(e.id) == str(experiment_id)), None
            )
            if not experiment:
                raise ExperimentNotAccessibleError(
                    f"Experiment {experiment_id} not found in project {project_id}"
                )
            if not await self.permission_checker.can_edit_experiment(
                user.id, experiment.project_id
            ):
                raise ExperimentNotAccessibleError(
                    f"You are not allowed to edit experiment {experiment_id}"
                )
            await self.experiment_repository.update(experiment_id, order=i)
        await self.db.commit()
        return True

    async def get_experiments_by_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(),
        *,
        search: str | None = None,
        include_features: bool = True,
    ) -> ExperimentListResponseDTO:
        if not await self.permission_checker.can_view_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to view experiments in project {project_id}"
            )
        experiments_page = await self.experiment_repository.get_experiments_by_project(
            project_id,
            list_options=list_options,
            search=search,
            include_features=include_features,
        )
        return ExperimentListResponseDTO.from_page(
            experiments_page.map(
                lambda experiment: self.experiment_mapper.experiment_schema_to_list_item_dto(
                    experiment, include_features=include_features
                )
            )
        )

    async def get_experiments_batch_for_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        experiment_ids: List[UUID_TYPE],
        *,
        include_features: bool = True,
    ) -> ExperimentListResponseDTO:
        if not await self.permission_checker.can_view_experiment(user.id, project_id):
            raise ExperimentNotAccessibleError(
                f"You are not allowed to view experiments in project {project_id}"
            )
        unique_ids = list(dict.fromkeys(experiment_ids))
        rows = await self.experiment_repository.get_experiments_by_ids(
            unique_ids, include_features=include_features
        )
        by_id = {e.id: e for e in rows if e.project_id == project_id}
        ordered = [by_id[eid] for eid in unique_ids if eid in by_id]
        dtos = [
            self.experiment_mapper.experiment_schema_to_list_item_dto(
                e, include_features=include_features
            )
            for e in ordered
        ]
        return ExperimentListResponseDTO(
            data=dtos,
            has_next=False,
            size=len(dtos),
            total=len(dtos),
        )
