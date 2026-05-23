"""Healthcheck DTO — JSON field names match the backend wire format (camelCase)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthCheckResponse(BaseModel):
    """Response shape for ``GET /`` (API root under configured prefix)."""

    status: Literal["ok"]
    service: str
    version: str

    model_config = ConfigDict(extra="forbid")
