from datetime import datetime

from experiment_tracker_shared.scalar_values import ScalarWireValue, scalar_to_wire
from pydantic import BaseModel, field_serializer

from ...pagination import PaginatedResponse


class StepTagsResponse(BaseModel):
    step: int
    scalar_names: list[str]
    tags: list[str]


class ScalarSeriesResponse(BaseModel):
    x: list[int]
    y: list[ScalarWireValue]


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

    @field_serializer("scalars")
    def _serialize_scalars(
        self, scalars: dict[str, float]
    ) -> dict[str, ScalarWireValue]:
        return {name: scalar_to_wire(value) for name, value in scalars.items()}


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
