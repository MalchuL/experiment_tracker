from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.artifacts_info.dto import (
    ArtifactInfoSummaryEntryDTO,
    ExperimentArtifactsSummaryDTO,
)
from app.domain.artifacts_info.service import ArtifactsInfoService
from app.infrastructure.cache.in_memory_cache import InMemoryCache


@pytest.mark.asyncio
async def test_artifacts_summary_cache_is_per_experiment_and_name() -> None:
    """Summary cache entries are reusable per experiment, but isolated by artifact name."""
    project_id = uuid4()
    experiment_id = uuid4()
    service = ArtifactsInfoService(client=object(), cache=InMemoryCache(ttl_seconds=60))
    summary = ExperimentArtifactsSummaryDTO(
        experiment_id=experiment_id,
        artifacts_info=[
            ArtifactInfoSummaryEntryDTO(
                name="predictions",
                artifact_type="image",
                steps=[1, 2],
                last_modified=datetime(2026, 1, 1, 0, 0, 0),
            )
        ],
    )

    await service._store_artifacts_summary_cache(
        project_id=project_id,
        merged=[summary],
        skip_experiment_ids=frozenset(),
        artifact_types=["image"],
        artifact_names=["predictions"],
        max_steps=100,
        start_time=None,
        end_time=None,
    )

    cached_full, cached_by_exp = await service._get_artifacts_summary_try_cache(
        project_id=project_id,
        page_ids=[experiment_id],
        total_experiments=1,
        artifact_types=["image"],
        artifact_names=["predictions"],
        max_steps=100,
        limit=10,
        offset=0,
        start_time=None,
        end_time=None,
    )
    assert cached_full is not None
    assert cached_full.data == [summary]
    assert cached_by_exp == {}

    other_name_full, other_name_hits = await service._get_artifacts_summary_try_cache(
        project_id=project_id,
        page_ids=[experiment_id],
        total_experiments=1,
        artifact_types=["image"],
        artifact_names=["labels"],
        max_steps=100,
        limit=10,
        offset=0,
        start_time=None,
        end_time=None,
    )
    assert other_name_full is None
    assert other_name_hits == {}


@pytest.mark.asyncio
async def test_artifacts_summary_cache_skips_time_bounded_queries() -> None:
    """Live-refresh summary queries bypass cache because their bounds define freshness."""
    project_id = uuid4()
    experiment_id = uuid4()
    service = ArtifactsInfoService(client=object(), cache=InMemoryCache(ttl_seconds=60))
    summary = ExperimentArtifactsSummaryDTO(
        experiment_id=experiment_id,
        artifacts_info=[
            ArtifactInfoSummaryEntryDTO(
                name="predictions",
                artifact_type="image",
                steps=[1],
                last_modified=datetime(2026, 1, 1, 0, 0, 0),
            )
        ],
    )

    await service._store_artifacts_summary_cache(
        project_id=project_id,
        merged=[summary],
        skip_experiment_ids=frozenset(),
        artifact_types=["image"],
        artifact_names=["predictions"],
        max_steps=100,
        start_time=None,
        end_time=None,
    )
    cached_full, cached_by_exp = await service._get_artifacts_summary_try_cache(
        project_id=project_id,
        page_ids=[experiment_id],
        total_experiments=1,
        artifact_types=["image"],
        artifact_names=["predictions"],
        max_steps=100,
        limit=10,
        offset=0,
        start_time=datetime(2026, 1, 1, 0, 0, 0),
        end_time=None,
    )

    assert cached_full is None
    assert cached_by_exp == {}


@pytest.mark.asyncio
async def test_artifacts_summary_cache_invalidates_one_experiment() -> None:
    """Artifact summary writes evict the changed experiment without clearing siblings."""
    project_id = uuid4()
    experiment_a = uuid4()
    experiment_b = uuid4()
    service = ArtifactsInfoService(client=object(), cache=InMemoryCache(ttl_seconds=60))
    summary_a = ExperimentArtifactsSummaryDTO(
        experiment_id=experiment_a,
        artifacts_info=[
            ArtifactInfoSummaryEntryDTO(
                name="predictions",
                artifact_type="image",
                steps=[1],
                last_modified=datetime(2026, 1, 1, 0, 0, 0),
            )
        ],
    )
    summary_b = ExperimentArtifactsSummaryDTO(
        experiment_id=experiment_b,
        artifacts_info=[
            ArtifactInfoSummaryEntryDTO(
                name="predictions",
                artifact_type="image",
                steps=[1],
                last_modified=datetime(2026, 1, 1, 0, 0, 0),
            )
        ],
    )
    await service._store_artifacts_summary_cache(
        project_id=project_id,
        merged=[summary_a, summary_b],
        skip_experiment_ids=frozenset(),
        artifact_types=["image"],
        artifact_names=["predictions"],
        max_steps=100,
        start_time=None,
        end_time=None,
    )

    await service._invalidate_summary_cache(project_id, experiment_a)

    cached_full, cached_by_exp = await service._get_artifacts_summary_try_cache(
        project_id=project_id,
        page_ids=[experiment_a, experiment_b],
        total_experiments=2,
        artifact_types=["image"],
        artifact_names=["predictions"],
        max_steps=100,
        limit=10,
        offset=0,
        start_time=None,
        end_time=None,
    )

    assert cached_full is None
    assert cached_by_exp == {experiment_b: summary_b}
