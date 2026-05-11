from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel

from app.lib.dto_config import model_config


class CreateProjectTableDTO(BaseModel):
    model_config = model_config()

    project_id: UUID


class CreateProjectTableResponseDTO(BaseModel):
    model_config = model_config()

    table_name: str
    project_id: UUID


class GetProjectTableExistenceDTO(BaseModel):
    model_config = model_config()

    table_name: str
    project_id: UUID
    exists: bool


class DeleteProjectTableResponseDTO(BaseModel):
    model_config = model_config()

    message: str


@dataclass(slots=True)
class ClickhouseTableUsageStats:
    """Per-table usage row used inside the service before mapping to HTTP DTOs."""

    table: str
    exists: bool
    rows: int
    columns: int
    bytes: int


class ClickhouseTableUsageStatsDTO(BaseModel):
    model_config = model_config()

    table: str
    exists: bool
    rows: int
    columns: int
    bytes: int


class ProjectClickhouseUsageResponseDTO(BaseModel):
    model_config = model_config()

    project_id: UUID
    total_bytes: int
    tables: list[ClickhouseTableUsageStatsDTO]


class ExperimentClickhouseUsageResponseDTO(BaseModel):
    model_config = model_config()

    project_id: UUID
    experiment_id: UUID
    rows: int
    bytes: int


class DeleteExperimentScalarsDataResponseDTO(BaseModel):
    model_config = model_config()

    deleted: bool


class StorageTableRowDTO(BaseModel):
    model_config = model_config()

    name: str
    rows: int
    bytes: int


class ListStorageTablesResponseDTO(BaseModel):
    model_config = model_config()

    tables: list[StorageTableRowDTO]
    total: int
    limit: int
    offset: int


class DropManagedStorageTableResponseDTO(BaseModel):
    model_config = model_config()

    dropped: bool
    table: str
