"""About response for ``GET /about`` (no auth required)."""

from __future__ import annotations

import importlib.metadata

from pydantic import BaseModel

from lib.dto_config import model_config

PACKAGE_NAME = "experiment-tracker-backend"

ABOUT_DESCRIPTION = (
    "ML experiment tracking: projects, experiments, metrics, and file artifacts."
)


def get_backend_version() -> str:
    try:
        return importlib.metadata.version(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"


class AboutResponseDTO(BaseModel):
    """Public build and product metadata for the main API."""

    service: str
    version: str
    description: str = ABOUT_DESCRIPTION

    model_config = model_config()
