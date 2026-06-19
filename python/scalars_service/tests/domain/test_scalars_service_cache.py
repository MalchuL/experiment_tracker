from uuid import uuid4

import pytest

from app.domain.scalars.dto import ExperimentsScalarsPointsResultDTO, ScalarsSampling
from app.domain.scalars.service import ScalarsService
from app.infrastructure.cache.in_memory_cache import InMemoryCache


@pytest.mark.asyncio
async def test_query_scalar_columns_filters_requested_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    service = ScalarsService(client=object())

    async def get_scalar_columns(table_name: str) -> list[str]:
        _ = table_name
        return ["c_loss", "c_acc", "legacy_col"]

    async def get_mapping(project_id_arg):
        _ = project_id_arg
        return {"loss": "c_loss", "accuracy": "c_acc"}

    monkeypatch.setattr(service, "_get_scalar_columns", get_scalar_columns)
    monkeypatch.setattr(service, "_get_or_create_scalar_mapping", get_mapping)

    all_columns = await service._get_query_scalar_columns(
        project_id=project_id,
        table_name="scalars_test",
        scalar_names=None,
    )
    assert all_columns == {
        "c_loss": "loss",
        "c_acc": "accuracy",
        "legacy_col": "legacy_col",
    }

    filtered = await service._get_query_scalar_columns(
        project_id=project_id,
        table_name="scalars_test",
        scalar_names=["loss"],
    )
    assert filtered == {"c_loss": "loss"}

    unknown = await service._get_query_scalar_columns(
        project_id=project_id,
        table_name="scalars_test",
        scalar_names=["missing"],
    )
    assert unknown == {}


@pytest.mark.asyncio
async def test_scalars_cache_is_isolated_by_scalar_names() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    service = ScalarsService(client=object(), cache=InMemoryCache(ttl_seconds=60))
    summary = ExperimentsScalarsPointsResultDTO(
        experiment_id=experiment_id,
        scalars={},
    )

    await service._store_get_scalars_cache(
        project_id=project_id,
        merged=[summary],
        skip_experiment_ids=frozenset(),
        max_points=100,
        return_tags=False,
        scalar_names=["loss"],
        store_cache=True,
        start_time=None,
        end_time=None,
        start_step=None,
        end_step=None,
        sampling=ScalarsSampling.UNIFORM,
        columns_per_query=1,
    )

    cached_full, cached_by_exp = await service._get_scalars_try_cache(
        project_id=project_id,
        page_ids=[experiment_id],
        total_experiments=1,
        max_points=100,
        return_tags=False,
        scalar_names=["loss"],
        store_cache=True,
        start_time=None,
        end_time=None,
        start_step=None,
        end_step=None,
        sampling=ScalarsSampling.UNIFORM,
        columns_per_query=1,
        limit=10,
        offset=0,
    )
    assert cached_full is not None
    assert cached_full.data == [summary]
    assert cached_by_exp == {}

    other_full, other_hits = await service._get_scalars_try_cache(
        project_id=project_id,
        page_ids=[experiment_id],
        total_experiments=1,
        max_points=100,
        return_tags=False,
        scalar_names=["accuracy"],
        store_cache=True,
        start_time=None,
        end_time=None,
        start_step=None,
        end_step=None,
        sampling=ScalarsSampling.UNIFORM,
        columns_per_query=1,
        limit=10,
        offset=0,
    )
    assert other_full is None
    assert other_hits == {}


@pytest.mark.asyncio
async def test_scalars_cache_store_cache_false_skips_read_and_write() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    service = ScalarsService(client=object(), cache=InMemoryCache(ttl_seconds=60))
    summary = ExperimentsScalarsPointsResultDTO(
        experiment_id=experiment_id,
        scalars={},
    )

    await service._store_get_scalars_cache(
        project_id=project_id,
        merged=[summary],
        skip_experiment_ids=frozenset(),
        max_points=100,
        return_tags=False,
        scalar_names=["loss"],
        store_cache=False,
        start_time=None,
        end_time=None,
        start_step=None,
        end_step=None,
        sampling=ScalarsSampling.UNIFORM,
        columns_per_query=1,
    )

    cached_full, cached_by_exp = await service._get_scalars_try_cache(
        project_id=project_id,
        page_ids=[experiment_id],
        total_experiments=1,
        max_points=100,
        return_tags=False,
        scalar_names=["loss"],
        store_cache=True,
        start_time=None,
        end_time=None,
        start_step=None,
        end_step=None,
        sampling=ScalarsSampling.UNIFORM,
        columns_per_query=1,
        limit=10,
        offset=0,
    )
    assert cached_full is None
    assert cached_by_exp == {}

    await service._store_get_scalars_cache(
        project_id=project_id,
        merged=[summary],
        skip_experiment_ids=frozenset(),
        max_points=100,
        return_tags=False,
        scalar_names=["loss"],
        store_cache=True,
        start_time=None,
        end_time=None,
        start_step=None,
        end_step=None,
        sampling=ScalarsSampling.UNIFORM,
        columns_per_query=1,
    )
    skipped_full, skipped_hits = await service._get_scalars_try_cache(
        project_id=project_id,
        page_ids=[experiment_id],
        total_experiments=1,
        max_points=100,
        return_tags=False,
        scalar_names=["loss"],
        store_cache=False,
        start_time=None,
        end_time=None,
        start_step=None,
        end_step=None,
        sampling=ScalarsSampling.UNIFORM,
        columns_per_query=1,
        limit=10,
        offset=0,
    )
    assert skipped_full is None
    assert skipped_hits == {}
