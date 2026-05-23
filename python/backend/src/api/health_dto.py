"""Healthcheck response for ``GET /`` (API root under configured prefix)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from lib.dto_config import model_config

API_VERSION = "1.0.0"


class HealthCheckResponseDTO(BaseModel):
    """Liveness payload returned by the API root."""

    status: Literal["ok"] = "ok"
    service: str
    version: str = API_VERSION

    model_config = model_config()
