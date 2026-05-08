"""Build ``CategoryCleanupResponseDTO``-shaped payloads for hard deletes (experiment / project / team / user)."""

from __future__ import annotations

from uuid import UUID

from domain.projects.dto import ProjectSatelliteTeardownDTO
from lib.category_cleanup_dto import (
    CategoryCleanupErrorEntryDTO,
    CategoryCleanupResponseDTO,
    CategoryCleanupResultEntryDTO,
)
from lib.satellite_step_dto import SatelliteStepDTO


def append_satellite_step(
    results: list[CategoryCleanupResultEntryDTO],
    errors: list[CategoryCleanupErrorEntryDTO],
    category: str,
    step: SatelliteStepDTO,
) -> None:
    """Record one ``run_satellite`` outcome as either a result row or an error row."""
    if step.ok:
        results.append(
            CategoryCleanupResultEntryDTO(
                category=category,
                result={"ok": True, "skipped": step.skipped},
            )
        )
    else:
        errors.append(
            CategoryCleanupErrorEntryDTO(
                category=category,
                error=step.error_message or "failed",
            )
        )


def finalize_deletion_outcome(
    results: list[CategoryCleanupResultEntryDTO],
    errors: list[CategoryCleanupErrorEntryDTO],
) -> CategoryCleanupResponseDTO:
    """Same semantics as category cleanup: ``success`` means no error rows."""
    return CategoryCleanupResponseDTO(
        success=len(errors) == 0,
        partial=bool(results and errors),
        results=results,
        errors=errors,
    )


def outcome_lists_from_project_teardown(
    teardown: ProjectSatelliteTeardownDTO,
) -> tuple[list[CategoryCleanupResultEntryDTO], list[CategoryCleanupErrorEntryDTO]]:
    """Flatten one project's satellite teardown into parallel results/errors lists."""
    results: list[CategoryCleanupResultEntryDTO] = []
    errors: list[CategoryCleanupErrorEntryDTO] = []
    pid = str(teardown.project_id)
    for row in teardown.experiments:
        eid = str(row.experiment_id)
        base = f"project:{pid}:experiment:{eid}"
        append_satellite_step(results, errors, f"{base}:objectStorage", row.object_storage)
        append_satellite_step(results, errors, f"{base}:scalars", row.scalars)
    append_satellite_step(
        results, errors, f"project:{pid}:objectStorage", teardown.project_object_storage
    )
    append_satellite_step(results, errors, f"project:{pid}:scalars", teardown.project_scalars)
    return results, errors


def append_postgres_deleted(
    results: list[CategoryCleanupResultEntryDTO],
    *,
    category: str,
    entity_id: UUID | None = None,
) -> None:
    payload: dict = {"deleted": True}
    if entity_id is not None:
        payload["id"] = str(entity_id)
    results.append(CategoryCleanupResultEntryDTO(category=category, result=payload))
