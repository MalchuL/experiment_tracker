from datetime import datetime
from pydantic import BaseModel

from ...pagination import PaginatedResponse


class StepTagsResponse(BaseModel):
    step: int
    scalar_names: list[str]
    tags: list[str]


class ScalarSeriesResponse(BaseModel):
    x: list[int]
    y: list[float]


class ExperimentScalarsPointsResponse(BaseModel):
    experiment_id: str
    scalars: dict[str, ScalarSeriesResponse]
    tags: list[StepTagsResponse] | None = None


class ScalarsPointsResponse(PaginatedResponse[ExperimentScalarsPointsResponse]):
    pass


class LogScalarRequest(BaseModel):
    scalars: dict[str, float]
    step: int
    tags: list[str] | None = None


class LogScalarsRequest(BaseModel):
    scalars: list[LogScalarRequest]


class LogScalarResponse(BaseModel):
    status: str
    warnings: list[str] | None = None


class LogScalarsResponse(BaseModel):
    status: str
    warnings: list[str] | None = None


class LastLoggedExperimentsRequest(BaseModel):
    experiment_ids: list[str] | None = None


class LastLoggedExperimentResponse(BaseModel):
    experiment_id: str
    last_modified: datetime


class LastLoggedExperimentsResponse(PaginatedResponse[LastLoggedExperimentResponse]):
    pass
