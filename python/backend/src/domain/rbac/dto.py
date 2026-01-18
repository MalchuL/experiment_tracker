# schemas/permissions.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from uuid import UUID

from lib.dto_config import model_config


class PermissionDTO(BaseModel):
    """Одно право"""

    user_id: UUID
    action: str = Field(..., description="create_experiment, delete_metric")
    allowed: bool
    team_id: Optional[UUID] = None
    project_id: Optional[UUID] = None

    model_config = model_config()


class PermissionListDTO(BaseModel):
    """Список прав пользователя"""

    data: List[PermissionDTO]

    model_config = model_config()
