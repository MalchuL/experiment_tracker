from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from experiment_tracker_shared.datetime_utc import to_json_utc_z
from experiment_tracker_shared.scalar_values import ScalarWireValue
from pydantic import BaseModel, Field

from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse


class ScalarsSampling(str, Enum):
    """Must stay aligned with scalars_service ``ScalarsSampling`` query values."""

    UNIFORM = "uniform"


class CreateProjectTableRequestDTO(BaseModel):
    model_config = model_config()

    project_id: UUID


class CreateProjectTableResponseDTO(BaseModel):
    model_config = model_config()

    table_name: str
    project_id: UUID


class ScalarsDeleteProjectTablesResponseDTO(BaseModel):
    model_config = model_config()

    message: str


class ScalarsDeleteExperimentDataResponseDTO(BaseModel):
    model_config = model_config()

    deleted: bool


class ScalarsCompactColumnsResponseDTO(BaseModel):
    model_config = model_config()

    dropped_columns: list[str] = Field(default_factory=list)


class ScalarsTableUsageDTO(BaseModel):
    model_config = model_config()

    table: str
    exists: bool
    rows: int
    columns: int
    bytes: int


class ScalarsProjectUsageResponseDTO(BaseModel):
    model_config = model_config()

    project_id: UUID
    total_bytes: int
    tables: list[ScalarsTableUsageDTO]


class ScalarsExperimentUsageResponseDTO(BaseModel):
    model_config = model_config()

    project_id: UUID
    experiment_id: UUID
    rows: int
    bytes: int


class ScalarsStorageTableRowDTO(BaseModel):
    model_config = model_config()

    name: str
    rows: int
    bytes: int


class ScalarsListStorageTablesResponseDTO(BaseModel):
    model_config = model_config()

    tables: list[ScalarsStorageTableRowDTO]
    total: int
    limit: int
    offset: int


class ScalarsDropStorageTableResponseDTO(BaseModel):
    model_config = model_config()

    dropped: bool
    table: str


class LogScalarRequestDTO(BaseModel):
    model_config = model_config()

    scalars: dict[str, ScalarWireValue]
    step: int
    tags: list[str] | None = None


class LogScalarsBatchRequestDTO(BaseModel):
    scalars: list[LogScalarRequestDTO]


class LogScalarResponseDTO(BaseModel):
    status: str
    warnings: list[str] | None = None


class ScalarSeriesDTO(BaseModel):
    x: list[int]
    y: list[ScalarWireValue]


class StepTagsDTO(BaseModel):
    step: int
    scalar_names: list[str]
    tags: list[str]


class ExperimentScalarsDTO(BaseModel):
    experiment_id: UUID
    scalars: dict[str, ScalarSeriesDTO]
    tags: list[StepTagsDTO] | None = None


class GetScalarsResponseDTO(PaginatedResponse[ExperimentScalarsDTO]):
    pass


class ScalarNamesResponseDTO(BaseModel):
    scalar_names: list[str]


class LastLoggedExperimentsRequestDTO(BaseModel):
    experiment_ids: list[UUID] | None = None


class LastLoggedExperimentDTO(BaseModel):
    experiment_id: UUID
    last_modified: ApiDateTime


class LastLoggedExperimentsResponseDTO(PaginatedResponse[LastLoggedExperimentDTO]):
    pass


class ScalarsQueryDTO(BaseModel):
    project_id: UUID
    experiment_ids: list[UUID] | None = None
    limit: int | None = None
    offset: int | None = None
    max_points: int | None = None
    sampling: ScalarsSampling = ScalarsSampling.UNIFORM
    columns_per_query: int = 1
    return_tags: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None
    start_step: int | None = None
    end_step: int | None = None
    scalar_names: list[str] | None = None
    store_cache: bool = True

    def as_query_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "return_tags": self.return_tags,
            "sampling": self.sampling.value,
            "columns_per_query": self.columns_per_query,
            "store_cache": self.store_cache,
        }
        if self.experiment_ids:
            params["experiment_id"] = [str(experiment_id) for experiment_id in self.experiment_ids]
        if self.limit is not None:
            params["limit"] = self.limit
        if self.offset is not None:
            params["offset"] = self.offset
        if self.max_points is not None:
            params["max_points"] = self.max_points
        if self.start_time is not None:
            params["start_time"] = to_json_utc_z(self.start_time)
        if self.end_time is not None:
            params["end_time"] = to_json_utc_z(self.end_time)
        if self.start_step is not None:
            params["start_step"] = self.start_step
        if self.end_step is not None:
            params["end_step"] = self.end_step
        if self.scalar_names is not None:
            params["scalar_name"] = self.scalar_names
        return params
