from pydantic import BaseModel, Field
from typing import Optional, List
from models import HypothesisStatus


class HypothesisBase(BaseModel):
    projectId: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    author: str = Field(..., min_length=1)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    targetMetrics: List[str] = []
    baseline: str = "root"


class HypothesisCreate(HypothesisBase):
    pass


class HypothesisUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    author: Optional[str] = None
    status: Optional[HypothesisStatus] = None
    targetMetrics: Optional[List[str]] = None
    baseline: Optional[str] = None


class Hypothesis(HypothesisBase):
    id: str
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True
