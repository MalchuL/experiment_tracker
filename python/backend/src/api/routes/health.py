"""Unauthenticated API root healthcheck."""

from __future__ import annotations

from fastapi import APIRouter

from api.health_dto import HealthCheckResponseDTO
from config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthCheckResponseDTO)
async def healthcheck() -> HealthCheckResponseDTO:
    """Return service identity and version (no auth required)."""
    settings = get_settings()
    return HealthCheckResponseDTO(service=settings.app_name)
