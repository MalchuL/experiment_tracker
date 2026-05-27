from __future__ import annotations

from domain.projects.errors import ProjectNotAccessibleError
from domain.rbac.wrapper import PermissionChecker
from lib.db.base_repository import DBNotFoundError
from lib.pagination import ListOptions
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from sqlalchemy.ext.asyncio import AsyncSession

from .dto import (
    ProjectReportCreateDTO,
    ProjectReportDTO,
    ProjectReportListResponseDTO,
    ProjectReportUpdateDTO,
)
from .error import ReportNotAccessibleError, ReportNotFoundError
from .mapper import ProjectReportMapper
from .repository import ProjectReportRepository


class ProjectReportService:
    """Application service for persisted project report documents.

    The service owns report CRUD operations, maps ORM rows to API DTOs, enforces
    project-scoped report permissions before every read or write, and commits
    successful mutations through the injected database session.
    """

    def __init__(
        self,
        db: AsyncSession,
        report_repository: ProjectReportRepository,
        permission_checker: PermissionChecker,
    ):
        self.db = db
        self.report_repository = report_repository
        self.permission_checker = permission_checker
        self.mapper = ProjectReportMapper()

    async def get_reports_by_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(),
    ) -> ProjectReportListResponseDTO:
        """List report summaries for a project.

        Args:
            user: User requesting the project reports.
            project_id: Project whose reports should be listed.
            list_options: Pagination limit and offset.

        Returns:
            ProjectReportListResponseDTO: Paginated report summaries.

        Raises:
            ProjectNotAccessibleError: If the user cannot view reports in the project.
        """
        if not await self.permission_checker.can_view_report(user.id, project_id):
            raise ProjectNotAccessibleError(f"Project {project_id} not accessible")
        page = await self.report_repository.get_reports_by_project(
            project_id,
            list_options=list_options,
        )
        return ProjectReportListResponseDTO.from_page(
            page.map(self.mapper.report_to_summary_dto)
        )

    async def get_report_if_accessible(
        self, user: UserProtocol, report_id: UUID_TYPE
    ) -> ProjectReportDTO:
        """Load a full report after verifying visibility.

        Args:
            user: User requesting the report.
            report_id: Report identifier.

        Returns:
            ProjectReportDTO: Full report content and metadata.

        Raises:
            ReportNotFoundError: If no report row exists for ``report_id``.
            ReportNotAccessibleError: If the report exists but the user lacks view
                permission for its project.
        """
        try:
            report = await self.report_repository.get_by_id(report_id)
            if not report:
                raise ReportNotFoundError(f"Report {report_id} not found")
        except DBNotFoundError:
            raise ReportNotFoundError(f"Report {report_id} not found")
        if await self.permission_checker.can_view_report(user.id, report.project_id):
            return self.mapper.report_to_dto(report)
        raise ReportNotAccessibleError(f"Report {report_id} not accessible")

    async def create_report(
        self, user: UserProtocol, data: ProjectReportCreateDTO
    ) -> ProjectReportDTO:
        """Create a report in a project.

        Args:
            user: User creating the report.
            data: Create DTO containing project id and report fields.

        Returns:
            ProjectReportDTO: Persisted report after commit and reload.

        Raises:
            ReportNotAccessibleError: If the user cannot create reports in the
                target project.
        """
        if not await self.permission_checker.can_create_report(user.id, data.project_id):
            raise ReportNotAccessibleError(
                f"Project {data.project_id} not accessible for report create"
            )
        report = self.mapper.create_dto_to_schema(data)
        await self.report_repository.create(report)
        await self.db.commit()
        report = await self.report_repository.get_by_id(report.id)
        return self.mapper.report_to_dto(report)

    async def update_report(
        self, user: UserProtocol, report_id: UUID_TYPE, data: ProjectReportUpdateDTO
    ) -> ProjectReportDTO:
        """Update editable fields on an existing report.

        Args:
            user: User editing the report.
            report_id: Report identifier.
            data: Update DTO; unset fields are ignored by the mapper.

        Returns:
            ProjectReportDTO: Updated report after commit and reload.

        Raises:
            ReportNotFoundError: If the report does not exist.
            ReportNotAccessibleError: If the user cannot edit reports in the report's
                project.
        """
        try:
            report = await self.report_repository.get_by_id(report_id)
            if not report:
                raise ReportNotFoundError(f"Report {report_id} not found")
        except DBNotFoundError:
            raise ReportNotFoundError(f"Report {report_id} not found")
        if not await self.permission_checker.can_edit_report(user.id, report.project_id):
            raise ReportNotAccessibleError(f"Report {report_id} not accessible")
        updates = self.mapper.update_dto_to_update_dict(data)
        if updates:
            await self.report_repository.update(report_id, **updates)
        await self.db.commit()
        report = await self.report_repository.get_by_id(report_id)
        return self.mapper.report_to_dto(report)

    async def delete_report(self, user: UserProtocol, report_id: UUID_TYPE) -> bool:
        """Delete a report row.

        Args:
            user: User deleting the report.
            report_id: Report identifier.

        Returns:
            bool: ``True`` when at least one row was deleted, otherwise ``False``.

        Raises:
            ReportNotFoundError: If the report does not exist.
            ReportNotAccessibleError: If the user lacks delete permission in the
                report's project.
        """
        try:
            report = await self.report_repository.get_by_id(report_id)
            if not report:
                raise ReportNotFoundError(f"Report {report_id} not found")
        except DBNotFoundError:
            raise ReportNotFoundError(f"Report {report_id} not found")
        if not await self.permission_checker.can_delete_report(
            user.id, report.project_id
        ):
            raise ReportNotAccessibleError(f"Report {report_id} not accessible")
        deleted = await self.report_repository.delete(report_id)
        await self.db.commit()
        return deleted > 0
