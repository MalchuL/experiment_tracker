from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from domain.experiment_data.error import ExperimentDataNotAccessibleError
from domain.experiment_data.service import ExperimentDataService
from models import ExperimentDataType


class FakeExperimentRepository:
    def __init__(self, experiments: list[SimpleNamespace]):
        self.experiments = {experiment.id: experiment for experiment in experiments}

    async def get_by_id(self, experiment_id: UUID):
        return self.experiments[experiment_id]

    async def get_experiments_by_ids(
        self, experiment_ids: list[UUID], *, include_features: bool = True
    ):
        return [
            self.experiments[experiment_id]
            for experiment_id in experiment_ids
            if experiment_id in self.experiments
        ]


class FakeExperimentDataRepository:
    def __init__(self):
        self.rows: dict[UUID, SimpleNamespace] = {}

    async def get_by_experiment_and_type(self, experiment_id, data_type):
        assert data_type is ExperimentDataType.HPARAMS
        return self.rows.get(experiment_id)

    async def list_by_experiments_and_type(self, experiment_ids, data_type):
        assert data_type is ExperimentDataType.HPARAMS
        return [
            self.rows[experiment_id]
            for experiment_id in experiment_ids
            if experiment_id in self.rows
        ]

    async def create(self, row):
        now = datetime(2026, 6, 7)
        row.id = uuid4()
        row.created_at = now
        row.updated_at = now
        self.rows[row.experiment_id] = row
        return row

    async def update(self, row_id, **updates):
        row = next(row for row in self.rows.values() if row.id == row_id)
        for key, value in updates.items():
            setattr(row, key, value)
        row.updated_at = datetime(2026, 6, 8)
        return row

    async def delete_by_experiment_and_type(self, experiment_id, data_type):
        assert data_type is ExperimentDataType.HPARAMS
        return int(self.rows.pop(experiment_id, None) is not None)

    async def commit(self):
        return None


class FakePermissions:
    def __init__(self, *, view: bool = True, edit: bool = True):
        self.view = view
        self.edit = edit

    async def can_view_experiment(self, user_id, project_id):
        return self.view

    async def can_edit_experiment(self, user_id, project_id):
        return self.edit


def make_service(
    experiments: list[SimpleNamespace],
    *,
    view: bool = True,
    edit: bool = True,
) -> tuple[ExperimentDataService, FakeExperimentDataRepository]:
    data = FakeExperimentDataRepository()
    service = ExperimentDataService(
        FakeExperimentRepository(experiments),  # type: ignore[arg-type]
        data,  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        FakePermissions(view=view, edit=edit),  # type: ignore[arg-type]
    )
    return service, data


@pytest.mark.asyncio
async def test_hparams_create_replace_empty_and_delete() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    experiment = SimpleNamespace(id=experiment_id, project_id=project_id, name="run")
    user = SimpleNamespace(id=uuid4())
    service, _ = make_service([experiment])

    created = await service.upsert_hparams(
        user, experiment_id, {"optimizer": {"name": "adamw"}, "batch_size": 32}
    )
    replaced = await service.upsert_hparams(user, experiment_id, {})
    deleted = await service.delete_hparams(user, experiment_id)
    missing = await service.get_hparams(user, experiment_id)

    assert created.hparams == {"optimizer": {"name": "adamw"}, "batch_size": 32}
    assert replaced.hparams == {}
    assert deleted.hparams is None
    assert missing.hparams is None


@pytest.mark.asyncio
async def test_hparams_requires_view_and_edit_permissions() -> None:
    experiment = SimpleNamespace(id=uuid4(), project_id=uuid4(), name="run")
    user = SimpleNamespace(id=uuid4())
    view_service, _ = make_service([experiment], view=False)
    edit_service, _ = make_service([experiment], edit=False)

    with pytest.raises(ExperimentDataNotAccessibleError):
        await view_service.get_hparams(user, experiment.id)
    with pytest.raises(ExperimentDataNotAccessibleError):
        await edit_service.upsert_hparams(user, experiment.id, {})


@pytest.mark.asyncio
async def test_list_hparams_preserves_order_and_rejects_foreign_experiments() -> None:
    project_id = uuid4()
    first = SimpleNamespace(id=uuid4(), project_id=project_id, name="first")
    second = SimpleNamespace(id=uuid4(), project_id=project_id, name="second")
    foreign = SimpleNamespace(id=uuid4(), project_id=uuid4(), name="foreign")
    user = SimpleNamespace(id=uuid4())
    service, _ = make_service([first, second, foreign])
    await service.upsert_hparams(user, second.id, {"lr": 0.1})

    result = await service.list_hparams(
        user, project_id, [second.id, first.id, second.id]
    )

    assert [item.experiment_id for item in result.experiments] == [
        second.id,
        first.id,
        second.id,
    ]
    assert result.experiments[0].hparams == {"lr": 0.1}
    assert result.experiments[1].hparams is None

    with pytest.raises(ExperimentDataNotAccessibleError):
        await service.list_hparams(user, project_id, [first.id, foreign.id])
