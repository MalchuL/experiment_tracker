"""Unauthenticated product metadata."""

from __future__ import annotations

from fastapi import APIRouter

from api.about_dto import AboutResponseDTO, get_backend_version
from config.settings import get_settings

router = APIRouter(tags=["about"])


@router.get("/about", response_model=AboutResponseDTO)
async def about() -> AboutResponseDTO:
    """Return backend version and short product description (no auth required)."""
    settings = get_settings()
    return AboutResponseDTO(
        service=settings.app_name,
        version=get_backend_version(),
    )
