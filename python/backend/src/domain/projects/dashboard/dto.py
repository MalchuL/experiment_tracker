from pydantic import BaseModel, Field
from lib.dto_config import model_config


class DashboardStatsDTO(BaseModel):
    totalExperiments: int = Field(..., description="Total number of experiments")
    runningExperiments: int = Field(..., description="Number of running experiments")
    completedExperiments: int = Field(
        ..., description="Number of completed experiments"
    )
    failedExperiments: int = Field(..., description="Number of failed experiments")
    totalHypotheses: int = Field(..., description="Total number of hypotheses")
    supportedHypotheses: int = Field(..., description="Number of supported hypotheses")
    refutedHypotheses: int = Field(..., description="Number of refuted hypotheses")

    model_config = model_config()
