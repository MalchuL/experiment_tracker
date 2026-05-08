"""Admin route response models (non-domain-specific)."""

from __future__ import annotations

from lib.category_cleanup_dto import CategoryCleanupResponseDTO
from lib.dto_config import model_config


class AdminUserDeleteResponseDTO(CategoryCleanupResponseDTO):
    """Outcome of DELETE ``/admin/users/{id}`` (cleanup-shaped)."""

    model_config = model_config()
