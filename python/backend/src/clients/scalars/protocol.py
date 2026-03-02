from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .dto import (
    CreateProjectTableResponseDTO,
    GetScalarsResponseDTO,
    LastLoggedExperimentsRequestDTO,
    LastLoggedExperimentsResponseDTO,
    LogScalarsBatchRequestDTO,
    LogScalarRequestDTO,
    LogScalarResponseDTO,
    ScalarsQueryDTO,
)


class ScalarsClientProtocol(Protocol):
    async def create_project_table(
        self, project_id: UUID
    ) -> CreateProjectTableResponseDTO: ...

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarRequestDTO
    ) -> LogScalarResponseDTO: ...

    async def log_scalars_batch(
        self, project_id: UUID, experiment_id: UUID, payload: LogScalarsBatchRequestDTO
    ) -> LogScalarResponseDTO: ...

    async def get_scalars(self, query: ScalarsQueryDTO) -> GetScalarsResponseDTO: ...

    async def get_last_logged_experiments(
        self, project_id: UUID, payload: LastLoggedExperimentsRequestDTO
    ) -> LastLoggedExperimentsResponseDTO: ...

