from dataclasses import dataclass
from domain.projects.dto import ProjectCreateDTO, ProjectDTO, ProjectUpdateDTO
from models import Project
from typing import List, Optional, Sequence


@dataclass
class SchemaToDTOProps:
    experiment_count: int = 0  # Calculated from the experiments
    hypothesis_count: int = 0  # Calculated from the hypotheses


@dataclass
class CreateDTOToSchemaProps:
    owner_id: Optional[str] = None


@dataclass
class UpdateDTOToSchemaProps:
    owner_id: Optional[str] = None


class ProjectMapper:
    def project_schema_to_dto(
        self, project: Project, props: SchemaToDTOProps | None = None
    ) -> ProjectDTO:
        if props is None:
            props = SchemaToDTOProps()

        return ProjectDTO(
            id=str(project.id),
            name=project.name,
            description=project.description,
            owner=project.owner,
            ownerId=project.owner_id,
            createdAt=project.created_at,
            metrics=project.metrics,
            settings=project.settings,
            experimentCount=props.experiment_count,  # Does not exist in the schema
            hypothesisCount=props.hypothesis_count,  # Does not exist in the schema
            teamId=project.team_id,
            teamName=project.team.name if project.team else None,
        )

    def project_list_schema_to_dto(
        self,
        projects: Sequence[Project],
        props: Sequence[SchemaToDTOProps] | None = None,
    ) -> List[ProjectDTO]:
        if props is None:
            props = [SchemaToDTOProps() for _ in projects]

        if len(props) != len(projects):
            raise ValueError("The number of props must match the number of projects")

        return [
            self.project_schema_to_dto(project, prop)
            for project, prop in zip(projects, props)
        ]

    def project_create_dto_to_schema(
        self, dto: ProjectCreateDTO, props: CreateDTOToSchemaProps | None = None
    ) -> Project:
        if props is None:
            props = CreateDTOToSchemaProps()

        return Project(
            name=dto.name,
            description=dto.description,
            owner=dto.owner,
            owner_id=props.owner_id,
            team_id=dto.teamId,
            metrics=dto.metrics,
            settings=dto.settings,
        )

    def project_update_dto_to_schema(
        self, dto: ProjectUpdateDTO, props: UpdateDTOToSchemaProps | None = None
    ) -> Project:
        if props is None:
            props = UpdateDTOToSchemaProps()

        project = Project(
            owner_id=props.owner_id,
        )
        update_data = dto.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        return project
