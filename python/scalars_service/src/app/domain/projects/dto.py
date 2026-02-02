from pydantic import BaseModel


class CreateProjectTableDTO(BaseModel):
    project_id: str


class CreateProjectTableResponseDTO(BaseModel):
    table_name: str
    project_id: str


class GetProjectTableExistenceDTO(BaseModel):
    table_name: str
    project_id: str
    exists: bool


class DeleteProjectTableResponseDTO(BaseModel):
    message: str
