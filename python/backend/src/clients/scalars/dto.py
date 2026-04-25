from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from lib.pagination import PaginatedResponse


class ScalarsSampling(str, Enum):
    """Must stay aligned with scalars_service ``ScalarsSampling`` query values."""

    UNIFORM = "uniform"


class CreateProjectTableRequestDTO(BaseModel):
    project_id: UUID


class CreateProjectTableResponseDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None


class LogScalarRequestDTO(BaseModel):
    scalars: dict[str, float]
    step: int
    tags: list[str] | None = None


class LogScalarsBatchRequestDTO(BaseModel):
    scalars: list[LogScalarRequestDTO]


class LogScalarResponseDTO(BaseModel):
    status: str
    warnings: list[str] | None = None


class ScalarSeriesDTO(BaseModel):
    x: list[int]
    y: list[float]


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


class LastLoggedExperimentsRequestDTO(BaseModel):
    experiment_ids: list[UUID] | None = None


class LastLoggedExperimentDTO(BaseModel):
    experiment_id: UUID
    last_modified: datetime


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

    def as_query_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "return_tags": self.return_tags,
            "sampling": self.sampling.value,
            "columns_per_query": self.columns_per_query,
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
            params["start_time"] = self.start_time.isoformat()
        if self.end_time is not None:
            params["end_time"] = self.end_time.isoformat()
        return params

