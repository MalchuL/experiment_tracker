from __future__ import annotations

from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from lib.types import UUID_TYPE
from models import ProjectReport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only


class ProjectReportRepository(BaseRepository[ProjectReport]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ProjectReport)

    async def get_reports_by_project(
        self,
        project_id: UUID_TYPE,
        list_options: ListOptions | None = None,
    ) -> Page[ProjectReport]:
        summary_load = load_only(
            ProjectReport.id,
            ProjectReport.project_id,
            ProjectReport.title,
            ProjectReport.created_at,
            ProjectReport.updated_at,
        )
        return await self.list(
            ProjectReport.project_id == project_id,
            order_by=ProjectReport.updated_at.desc(),
            load=summary_load,
            list_options=list_options,
        )
