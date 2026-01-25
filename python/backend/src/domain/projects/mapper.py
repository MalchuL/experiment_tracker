from dataclasses import dataclass
from domain.projects.dto import (
    ProjectCreateDTO,
    ProjectDTO,
    ProjectOwnerDTO,
    ProjectTeamDTO,
    ProjectUpdateDTO,
)
from domain.projects.utils import default_metrics
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

        return ProjectDTO(
            id=str(project.id),
            name=project.name,
            description=project.description,
            owner=owner,
            created_at=project.created_at.isoformat() if project.created_at else "",
            metrics=project.metrics or [],
            settings=project.settings or {},
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
        # Convert metrics from Pydantic models to dicts
        converter = DtoConverter[ProjectCreateDTO](ProjectCreateDTO)
        metrics: List[Dict[str, Any]] = []
        if dto.metrics:
            metrics = [converter.dto_to_dict_with_dto_case(m) for m in dto.metrics]

        # Convert settings from Pydantic model to dict
        if dto.settings:
            settings = converter.dto_to_dict_with_dto_case(dto.settings)
        else:
            settings = default_metrics()  # Returns default settings dict

        # Note: owner_id comes from props (user.id), not from dto.owner
        # The dto.owner field is just for display purposes in the DTO
        return Project(
            name=dto.name,
            description=dto.description,
            owner_id=props.owner_id,
            team_id=dto.team_id if dto.team_id else None,
            metrics=metrics,
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
            metrics = []
            for m in converted_dto["metrics"]:
                metric = {
                    "name": m["name"],
                    "direction": m["direction"],
                    "aggregation": m["aggregation"],
                }
                metrics.append(metric)
            updates["metrics"] = metrics
        if "settings" in converted_dto:
            settings = {
                "naming_pattern": converted_dto["settings"]["naming_pattern"],
                "display_metrics": converted_dto["settings"]["display_metrics"],
            }
            updates["settings"] = settings

        return updates
