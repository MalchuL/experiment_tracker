"""Tests for :class:`NoOpExperimentArtifactsService`."""

from __future__ import annotations

import io
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import UploadFile

from clients.artifacts_info import ArtifactsInfoResultDTO
from domain.experiment_artifacts.error import ExperimentArtifactsNotAccessibleError
from domain.experiment_artifacts.noop_service import NoOpExperimentArtifactsService


@pytest.mark.asyncio
async def test_noop_list_returns_empty() -> None:
    svc = NoOpExperimentArtifactsService()
    out = await svc.list_experiment_artifacts(
        user=SimpleNamespace(id=uuid4()),
        experiment_id=uuid4(),
    )
    assert out == []


@pytest.mark.asyncio
async def test_noop_get_experiments_artifacts_at_step_returns_empty_data() -> None:
    svc = NoOpExperimentArtifactsService()
    result = await svc.get_experiments_artifacts_at_step(
        user=SimpleNamespace(id=uuid4()),
        project_id=uuid4(),
    )
    assert isinstance(result, ArtifactsInfoResultDTO)
    assert result.data == []


@pytest.mark.asyncio
async def test_noop_upsert_raises_not_accessible() -> None:
    svc = NoOpExperimentArtifactsService()
    with pytest.raises(ExperimentArtifactsNotAccessibleError):
        await svc.upsert_experiment_artifact(
            user=SimpleNamespace(id=uuid4()),
            experiment_id=uuid4(),
            name="a",
            filepath="b.txt",
            file=UploadFile(filename="b.txt", file=io.BytesIO(b"x")),
        )
