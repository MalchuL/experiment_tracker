"""HTTP routes under ``/reports`` for project report documents."""

from uuid import UUID

from api.routes.service_dependencies import get_project_report_service
from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions
from models import User
from domain.rbac.permissions import ProjectActions

from .dto import (
    ProjectReportCreateDTO,
    ProjectReportDTO,
    ProjectReportUpdateDTO,
)
from .error import ReportNotAccessibleError, ReportNotFoundError
from .service import ProjectReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def _raise_report_http_error(error: Exception) -> None:
    """Translate report-domain exceptions into HTTP responses.

    Args:
        error: Exception raised by ``ProjectReportService`` or persistence code.

    Raises:
        HTTPException: ``403`` for inaccessible reports, ``404`` for missing reports,
            and ``400`` for other report validation or repository errors.
    """
    if isinstance(error, ReportNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, ReportNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.get("/{report_id}", response_model=ProjectReportDTO)
async def get_report(
    report_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_REPORT)),
    report_service: ProjectReportService = Depends(get_project_report_service),
):
    """Return one project report document visible to the current user.

    Args:
        report_id: Identifier of the report to fetch.
        user: Authenticated user supplied by the auth dependency.
        _: API-token scope guard requiring report view access.
        report_service: Report application service dependency.

    Returns:
        ProjectReportDTO: Full report document payload for editors/readers.

    Raises:
        HTTPException: ``403`` when access is denied, ``404`` when the report does
            not exist, or ``400`` for other service errors.
    """
    try:
        return await report_service.get_report_if_accessible(user, report_id)
    except Exception as exc:  # noqa: BLE001
        _raise_report_http_error(exc)


@router.post("", response_model=ProjectReportDTO)
async def create_report(
    data: ProjectReportCreateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_REPORT)),
    report_service: ProjectReportService = Depends(get_project_report_service),
):
    """Create a report document in a project.

    Args:
        data: Report title/content/project payload from the request body.
        user: Authenticated user creating the report.
        _: API-token scope guard requiring report creation access.
        report_service: Report application service dependency.

    Returns:
        ProjectReportDTO: Newly persisted report with generated identifiers and
        timestamps.

    Raises:
        HTTPException: ``403`` when the user cannot create reports in the project,
            or ``400`` for validation and persistence errors.
    """
    try:
        return await report_service.create_report(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_report_http_error(exc)


@router.patch("/{report_id}", response_model=ProjectReportDTO)
async def update_report(
    report_id: UUID,
    data: ProjectReportUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_REPORT)),
    report_service: ProjectReportService = Depends(get_project_report_service),
):
    """Apply a partial update to a report document.

    Args:
        report_id: Identifier of the report to update.
        data: Patch payload containing editable report fields.
        user: Authenticated user performing the edit.
        _: API-token scope guard requiring report edit access.
        report_service: Report application service dependency.

    Returns:
        ProjectReportDTO: Updated report after persistence.

    Raises:
        HTTPException: ``403`` for insufficient project report permissions,
            ``404`` for a missing report, or ``400`` for other service errors.
    """
    try:
        return await report_service.update_report(user, report_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_report_http_error(exc)


@router.delete("/{report_id}")
async def delete_report(
    report_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_REPORT)),
    report_service: ProjectReportService = Depends(get_project_report_service),
):
    """Delete a report document.

    Args:
        report_id: Identifier of the report to remove.
        user: Authenticated user performing the delete.
        _: API-token scope guard requiring report delete access.
        report_service: Report application service dependency.

    Returns:
        dict[str, bool]: ``{"success": True}`` when the report row is deleted.

    Raises:
        HTTPException: ``403`` for insufficient delete permission, ``404`` when the
            report is missing or the repository reports no deleted row, and ``400``
            for other service errors.
    """
    try:
        success = await report_service.delete_report(user, report_id)
    except Exception as exc:  # noqa: BLE001
        _raise_report_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"success": True}
