"""Typed responses for danger-zone category cleanup (experiment / project scope)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from lib.dto_config import model_config


class CategoryCleanupResultEntryDTO(BaseModel):
    category: str
    result: dict[str, Any] = Field(default_factory=dict)

    model_config = model_config()


class CategoryCleanupErrorEntryDTO(BaseModel):
    category: str
    error: str

    model_config = model_config()


class CategoryCleanupResponseDTO(BaseModel):
    success: bool
    partial: bool
    results: list[CategoryCleanupResultEntryDTO] = Field(default_factory=list)
    errors: list[CategoryCleanupErrorEntryDTO] = Field(default_factory=list)

    model_config = model_config()
