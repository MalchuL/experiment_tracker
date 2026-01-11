from dataclasses import dataclass
from domain.projects.dto import ProjectCreateDTO, ProjectDTO, ProjectUpdateDTO
from domain.projects.utils import default_metrics
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

        # Extract owner name/email from relationship
        owner_str = (
            getattr(project.owner, "email", None)
            or getattr(project.owner, "display_name", None)
            or str(project.owner_id)
        )

        return ProjectDTO(
            id=str(project.id),
            name=project.name,
            description=project.description,
            owner=owner_str,
            ownerId=str(project.owner_id),
            createdAt=project.created_at.isoformat() if project.created_at else "",
            metrics=project.metrics or [],
            settings=project.settings or {},
            experimentCount=props.experiment_count,
            hypothesisCount=props.hypothesis_count,
            teamId=str(project.team_id) if project.team_id else None,
            teamName=project.team.name if project.team else None,
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
        metrics: List[Dict[str, Any]] = []
        if dto.metrics:
            metrics = [
                m.model_dump() if hasattr(m, "model_dump") else dict(m)
                for m in dto.metrics
            ]

        # Convert settings from Pydantic model to dict
        if dto.settings:
            settings = (
                dto.settings.model_dump()
                if hasattr(dto.settings, "model_dump")
                else dict(dto.settings)
            )
        else:
            settings = default_metrics()  # Returns default settings dict

        # Note: owner_id comes from props (user.id), not from dto.owner
        # The dto.owner field is just for display purposes in the DTO
        return Project(
            name=dto.name,
            description=dto.description,
            owner_id=props.owner_id,
            team_id=UUID(dto.teamId) if dto.teamId else None,
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
        updates: Dict[str, Any] = {}

        if dto.name is not None:
            updates["name"] = dto.name

        if dto.description is not None:
            updates["description"] = dto.description

        # Note: owner is a relationship, not a column, so we can't update it directly
        # To change the owner, you would need to update owner_id, which is not in UpdateDTO
        # If dto.owner is provided, we ignore it as it's not updatable via this endpoint

        # Convert metrics from Pydantic models to dicts if provided
        if dto.metrics is not None:
            updates["metrics"] = [
                m.model_dump() if hasattr(m, "model_dump") else dict(m)
                for m in dto.metrics
            ]

        # Convert settings from Pydantic model to dict if provided
        if dto.settings is not None:
            updates["settings"] = (
                dto.settings.model_dump()
                if hasattr(dto.settings, "model_dump")
                else dict(dto.settings)
            )

        return updates
