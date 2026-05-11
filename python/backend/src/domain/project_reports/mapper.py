from __future__ import annotations

from typing import Any

from lib.dto_converter import DtoConverter
from models import ProjectReport

from .dto import (
    ProjectReportCreateDTO,
    ProjectReportDTO,
    ProjectReportSummaryDTO,
    ProjectReportUpdateDTO,
)


DEFAULT_TIPTAP_DOC: dict[str, Any] = {
    "type": "doc",
    "content": [{"type": "paragraph"}],
}


class ProjectReportMapper:
    def report_to_summary_dto(self, report: ProjectReport) -> ProjectReportSummaryDTO:
        return ProjectReportSummaryDTO(
            id=report.id,
            project_id=report.project_id,
            title=report.title,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    def report_to_dto(self, report: ProjectReport) -> ProjectReportDTO:
        content = report.content if report.content else DEFAULT_TIPTAP_DOC
        return ProjectReportDTO(
            id=report.id,
            project_id=report.project_id,
            title=report.title,
            content=content,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    def create_dto_to_schema(self, data: ProjectReportCreateDTO) -> ProjectReport:
        content = data.content if data.content is not None else DEFAULT_TIPTAP_DOC
        return ProjectReport(
            project_id=data.project_id,
            title=data.title,
            content=content,
        )

    def update_dto_to_update_dict(self, data: ProjectReportUpdateDTO) -> dict[str, Any]:
        converter = DtoConverter[ProjectReportUpdateDTO](ProjectReportUpdateDTO)
        converted = converter.dto_to_partial_dict_with_dto_case(data)
        updates: dict[str, Any] = {}
        if "title" in converted:
            updates["title"] = converted["title"]
        if "content" in converted:
            updates["content"] = converted["content"]
        return updates
