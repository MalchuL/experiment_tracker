"""Best-effort satellite teardown for deleting a project (shared by project, team, admin flows)."""

from __future__ import annotations

from collections.abc import Sequence

from clients.object_storage import ObjectStorageClientProtocol
from domain.projects.dto import (
    ExperimentSatelliteTeardownDTO,
    ProjectSatelliteTeardownDTO,
)
from domain.scalars.service import ScalarsServiceProtocol
from lib.satellite_deletion import SatelliteCallResult, run_satellite
from lib.satellite_step_dto import satellite_step_from_result
from lib.types import UUID_TYPE


async def teardown_project_for_delete(
    project_id: UUID_TYPE,
    experiment_ids: Sequence[UUID_TYPE],
    object_storage_client: ObjectStorageClientProtocol | None,
    scalars_service: ScalarsServiceProtocol,
) -> ProjectSatelliteTeardownDTO:
    """Mirror ``ProjectService.delete_project`` satellite sequence without touching Postgres.

    For each experiment: object-storage delete all artifacts (if client configured), then
    scalars ``delete_experiment_data``. Then project-level object storage delete and scalars
    ``delete_project_table``.
    """
    experiment_steps: list[ExperimentSatelliteTeardownDTO] = []
    for experiment_id in experiment_ids:
        if object_storage_client is not None:
            os_raw = await run_satellite(
                object_storage_client.delete_all_experiment_artifacts(
                    project_id, experiment_id
                )
            )
        else:
            os_raw = SatelliteCallResult(ok=True, skipped=True)
        sc_raw = await run_satellite(
            scalars_service.delete_experiment_data(project_id, experiment_id)
        )
        experiment_steps.append(
            ExperimentSatelliteTeardownDTO(
                experiment_id=experiment_id,
                object_storage=satellite_step_from_result(os_raw),
                scalars=satellite_step_from_result(sc_raw),
            )
        )

    if object_storage_client is not None:
        proj_os_raw = await run_satellite(
            object_storage_client.delete_project(project_id)
        )
    else:
        proj_os_raw = SatelliteCallResult(ok=True, skipped=True)
    proj_sc_raw = await run_satellite(
        scalars_service.delete_project_table(project_id)
    )

    proj_os_dto = satellite_step_from_result(proj_os_raw)
    proj_sc_dto = satellite_step_from_result(proj_sc_raw)

    satellites_ok = (
        all(
            row.object_storage.ok and row.scalars.ok for row in experiment_steps
        )
        and proj_os_dto.ok
        and proj_sc_dto.ok
    )

    return ProjectSatelliteTeardownDTO(
        project_id=project_id,
        experiments=experiment_steps,
        project_object_storage=proj_os_dto,
        project_scalars=proj_sc_dto,
        satellites_ok=satellites_ok,
    )
