from pydantic import BaseModel


class DashboardStats(BaseModel):
    totalProjects: int
    totalExperiments: int
    runningExperiments: int
    completedExperiments: int
    failedExperiments: int
    totalHypotheses: int
    supportedHypotheses: int
    refutedHypotheses: int
