from dataclasses import dataclass
from domain.projects.dto import (
    ProjectCreateDTO,
    ProjectDTO,
    ProjectMetricKeyDTO,
    ProjectMetricsDTO,
    ProjectOwnerDTO,
    ProjectSettingDTO,
    ProjectTeamDTO,
    ProjectUpdateDTO,
    ProjectMetricDTO,
)
from domain.projects.utils import default_project_metrics
from lib.dto_converter import DtoConverter
from models import Project
from typing import List, Optional, Sequence, Dict, Any
from uuid import UUID


@dataclass
class SchemaToDTOProps:
    """Props for converting Project schema to DTO"""

    experiment_count: int = 0
    hypothesis_count: int = 0


@dataclass
class CreateDTOToSchemaProps:
    """Props for converting ProjectCreateDTO to Project schema"""

    owner_id: UUID


class ProjectMapper:
    """Mapper for converting between Project DTOs and SQLAlchemy models"""

    @staticmethod
    def _display_item_to_key(item: Any) -> Dict[str, Any]:
        if isinstance(item, str):
            return {"name": item, "label": None}
        if isinstance(item, dict):
            return {
                "name": str(item.get("name", "")),
                "label": item.get("label"),
            }
        return {"name": str(item), "label": None}

    @staticmethod
    def _normalize_metrics(
        metrics: Any, settings: Any | None = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        default_metrics = default_project_metrics()
        tracked_metrics: List[Dict[str, Any]] = []
        display_metrics: List[Dict[str, Any]] = []

        if isinstance(metrics, dict):
            tracked_raw = metrics.get("tracked_metrics", [])
            display_raw = metrics.get("display_metrics", [])
            if isinstance(tracked_raw, list):
                tracked_metrics = list(tracked_raw)
            if isinstance(display_raw, list):
                display_metrics = [
                    ProjectMapper._display_item_to_key(x) for x in display_raw
                ]
        elif isinstance(metrics, list):
            tracked_metrics = metrics
            if isinstance(settings, dict):
                legacy_display = settings.get("display_metrics", [])
                if isinstance(legacy_display, list):
                    display_metrics = [
                        ProjectMapper._display_item_to_key(x) for x in legacy_display
                    ]

        return {
            "tracked_metrics": tracked_metrics or default_metrics["tracked_metrics"],
            "display_metrics": display_metrics or default_metrics["display_metrics"],
        }

    @staticmethod
    def _normalize_settings(settings: Any) -> List[Dict[str, Any]]:
        if isinstance(settings, list):
            return settings
        return []

    def project_schema_to_dto(
        self, project: Project, props: SchemaToDTOProps
    ) -> ProjectDTO:
        """Convert Project model to ProjectDTO"""

        owner = ProjectOwnerDTO(
            id=project.owner.id,
            email=project.owner.email,
            display_name=project.owner.display_name,
        )

        if project.team_id:
            team = ProjectTeamDTO(
                id=project.team.id,
                name=project.team.name,
            )
        else:
            team = None

        normalized_metrics = self._normalize_metrics(project.metrics, project.settings)
        normalized_settings = self._normalize_settings(project.settings)

        tracked = [
            ProjectMetricDTO.model_validate(m) for m in normalized_metrics["tracked_metrics"]
        ]
        display = [
            ProjectMetricKeyDTO.model_validate(m) for m in normalized_metrics["display_metrics"]
        ]

        return ProjectDTO(
            id=str(project.id),
            name=project.name,
            description=project.description,
            owner=owner,
            created_at=project.created_at,
            metrics=ProjectMetricsDTO(
                tracked_metrics=tracked,
                display_metrics=display,
            ),
            settings=[
                ProjectSettingDTO.model_validate(item) for item in normalized_settings
            ],
            experiment_count=props.experiment_count,
            hypothesis_count=props.hypothesis_count,
            team=team,
        )

    def project_list_schema_to_dto(
        self,
        projects: Sequence[Project],
        props: Sequence[SchemaToDTOProps],
    ) -> List[ProjectDTO]:
        """Convert a list of Project models to ProjectDTOs"""

        if len(props) != len(projects):
            raise ValueError("The number of props must match the number of projects")

        return [
            self.project_schema_to_dto(project, prop)
            for project, prop in zip(projects, props)
        ]

    def project_create_dto_to_schema(
        self, dto: ProjectCreateDTO, props: CreateDTOToSchemaProps
    ) -> Project:
        """Convert ProjectCreateDTO to Project model"""
        converter = DtoConverter[ProjectCreateDTO](ProjectCreateDTO)
        converted_dto = converter.dto_to_dict_with_dto_case(dto)

        raw_metrics = converted_dto.get("metrics") or {}
        normalized_metrics = self._normalize_metrics(raw_metrics)
        settings = self._normalize_settings(converted_dto.get("settings", []))

        return Project(
            name=dto.name,
            description=dto.description,
            owner_id=props.owner_id,
            team_id=dto.team_id if dto.team_id else None,
            metrics=normalized_metrics,
            settings=settings,
        )

    def project_update_dto_to_update_dict(
        self, dto: ProjectUpdateDTO
    ) -> Dict[str, Any]:
        """
        Convert ProjectUpdateDTO to a dictionary of updates for repository.update()
        Only includes fields that are actually provided (not None)
        """
        converter = DtoConverter[ProjectUpdateDTO](ProjectUpdateDTO)
        converted_dto = converter.dto_to_partial_dict_with_dto_case(dto)
        updates = {}
        if "name" in converted_dto:
            updates["name"] = converted_dto["name"]
        if "description" in converted_dto:
            updates["description"] = converted_dto["description"]
        if "owner" in converted_dto:
            raise ValueError("Owner cannot be updated")
        if "metrics" in converted_dto:
            updates["metrics"] = self._normalize_metrics(converted_dto["metrics"])
        if "settings" in converted_dto:
            updates["settings"] = self._normalize_settings(converted_dto["settings"])

        return updates
