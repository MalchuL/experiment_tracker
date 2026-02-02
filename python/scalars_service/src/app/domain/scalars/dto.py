from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ScalarPointDTO(BaseModel):
    """Single scalar data point DTO"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    scalar_name: str
    value: float
    step: Optional[int] = None
    tags: Optional[Dict] = None


class ScalarsQueryDTO(BaseModel):
    """Query parameters for scalars DTO"""

    experiment_id: str
    scalar_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_points: Optional[int] = 500


class ScalarsExportRequestDTO(BaseModel):
    """Request parameters for scalars export DTO"""

    experiment_ids: Optional[List[str]] = None
    scalar_names: Optional[List[str]] = None
    include_all_experiments: bool = False


class ComparisonQueryDTO(BaseModel):
    """Query for comparing experiments DTO"""

    experiment_ids: List[str]
    scalar_name: str
    max_points: Optional[int] = 500


class ConvergenceStatsDTO(BaseModel):
    """Convergence analysis results DTO"""

    initial_value: float
    final_value: float
    total_improvement: float
    rate_per_step: float
    is_monotonic: bool
    total_logs: int


class ExperimentStatsDTO(BaseModel):
    """Basic experiment statistics DTO"""

    experiment_id: str
    total_logs: int
    scalar_count: int
    first_timestamp: datetime
    last_timestamp: datetime
    step_range: Dict[str, int]


class LogScalarRequestDTO(BaseModel):
    """Request DTO for logging a single scalar"""

    scalar_name: str
    value: float
    step: Optional[int] = None
    tags: Optional[Dict] = None
    timestamp: Optional[datetime] = None


class LogBatchRequestDTO(BaseModel):
    """Request DTO for logging multiple scalars"""

    scalars: Dict[str, float]
    step: Optional[int] = None
    tags: Optional[Dict] = None
    timestamp: Optional[datetime] = None
