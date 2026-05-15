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
    try:
        success = await report_service.delete_report(user, report_id)
    except Exception as exc:  # noqa: BLE001
        _raise_report_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"success": True}
