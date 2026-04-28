from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from lib.dto_config import model_config
from lib.pagination import PaginatedResponse
from lib.types import UUID_TYPE


class MetricBase(BaseModel):
    experiment_id: UUID_TYPE
    name: str = Field(..., min_length=1)
    value: float
    label: str | None = None
    model_config = model_config()

    @field_validator("label", mode="before")
    @classmethod
    def empty_string_label_is_none(cls, v: object) -> str | None:
        """Match DB semantics: unlabeled metrics use NULL, not empty string."""
        if v == "":
            return None
        return v  # type: ignore[return-value]


class MetricUpsertDTO(MetricBase):
    """Create or update the single metric row for (experiment_id, name, label), unique in DB."""

    model_config = model_config()


class MetricDTO(MetricBase):
    id: UUID_TYPE
    created_at: datetime

    model_config = model_config()


class MetricListResponseDTO(PaginatedResponse[MetricDTO]):
    model_config = model_config()


class MetricLabelsResponseDTO(BaseModel):
    """Distinct non-empty labels; null / unlabeled is reported via `has_unlabeled`."""

    labels: list[str] = Field(default_factory=list)
    has_unlabeled: bool = False

    model_config = model_config()


class UniqueMetricDimensionDTO(BaseModel):
    name: str
    label: str | None = None

    model_config = model_config()


class UniqueMetricDimensionsResponseDTO(BaseModel):
    items: list[UniqueMetricDimensionDTO] = Field(default_factory=list)

    model_config = model_config()


class MetricsByLabelRowDTO(BaseModel):
    experiment_id: UUID_TYPE
    experiment_name: str
    created_at: datetime
    color: str
    values: list[float | None]

    model_config = model_config()


class MetricsByLabelSnapshotResponseDTO(BaseModel):
    """Pivot table: columns follow `metric_names` order; each row aligns by index."""

    metric_names: list[str] = Field(default_factory=list)
    rows: list[MetricsByLabelRowDTO] = Field(default_factory=list)
    has_next: bool = False
    total: int = 0

    model_config = model_config()


