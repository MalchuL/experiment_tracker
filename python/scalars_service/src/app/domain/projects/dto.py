from uuid import UUID
from pydantic import BaseModel


class CreateProjectTableDTO(BaseModel):
    project_id: UUID


class CreateProjectTableResponseDTO(BaseModel):
    table_name: str
    project_id: UUID


class GetProjectTableExistenceDTO(BaseModel):
    table_name: str
    project_id: UUID
    exists: bool


class DeleteProjectTableResponseDTO(BaseModel):
    message: str
