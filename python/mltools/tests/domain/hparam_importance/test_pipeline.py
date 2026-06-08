"""Integration-style test for analysis training and persistence adapters."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mltools.domain.hparam_importance.analysis import run_analysis
from mltools.config.settings import Settings
from mltools.db.models import (
    Base,
    HparamImportanceJob,
    HparamImportanceModelArtifact,
    HparamImportanceResult,
)


class FakeBackend:
    """Provide deterministic experiment, hparam, and metric data to analysis."""

    def __init__(self, experiment_ids: list[UUID]):
        """Initialize the fake adapter.

        Args:
            experiment_ids: Ordered experiment identifiers exposed by the fake.

        Returns:
            None.
        """
        self.experiment_ids = experiment_ids

    async def list_experiments(self, project_id):
        """Return summaries for the configured experiments.

        Args:
            project_id: Ignored project identifier required by the port.

        Returns:
            Ordered experiment summary dictionaries.
        """
        return [
            {"id": str(experiment_id), "name": f"run-{index}"}
            for index, experiment_id in enumerate(self.experiment_ids)
        ]

    async def get_hparams(self, experiment_id):
        """Return deterministic nested hparams for one configured experiment.

        Args:
            experiment_id: Identifier whose position determines returned values.

        Returns:
            Nested hyperparameter document.
        """
        index = self.experiment_ids.index(experiment_id)
        return {
            "optimizer": {"lr": 0.001 * (index + 1), "name": "adam" if index % 2 else "sgd"},
            "seed": index,
        }

    async def get_aggregated_metrics(self, project_id, targets):
        """Return one deterministic loss value per configured experiment.

        Args:
            project_id: Ignored project identifier required by the port.
            targets: Ignored requested target list required by the port.

        Returns:
            Aggregate metric mapping keyed by the loss metric.
        """
        return {
            ("loss", None): {
                experiment_id: float(index)
                for index, experiment_id in enumerate(self.experiment_ids)
            }
        }


class FakeStorage:
    """Capture uploaded model artifacts in memory for assertions."""

    def __init__(self):
        """Initialize empty upload storage and a stable bucket name.

        Args:
            None.

        Returns:
            None.
        """
        self.uploads = {}
        self.bucket = "mltools"

    def upload(self, key, content):
        """Record an uploaded artifact.

        Args:
            key: Bucket-relative object key.
            content: Serialized artifact bytes.

        Returns:
            None.
        """
        self.uploads[key] = content


@pytest.mark.asyncio
async def test_analysis_trains_and_persists_results_and_artifact() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    experiments = [uuid4() for _ in range(8)]
    storage = FakeStorage()
    settings = Settings(
        min_experiments_per_metric=4,
        rf_n_estimators=10,
        rf_n_jobs=1,
        rf_test_size=0.25,
        object_storage_bucket="mltools",
    ).hparam_importance_settings()

    async with maker() as session:
        job = HparamImportanceJob(
            project_id=uuid4(),
            status="running",
            stage="building_dataset",
            progress=0.5,
            target_metrics=[{"name": "loss", "label": None}],
            config={
                "excluded_experiment_ids": [],
                "excluded_hparams": ["seed"],
                "parameter_overrides": {},
            },
        )
        session.add(job)
        await session.commit()
        successful = await run_analysis(
            session,
            job,
            backend=FakeBackend(experiments),  # type: ignore[arg-type]
            storage=storage,  # type: ignore[arg-type]
            settings=settings,
        )
        await session.commit()

        result_count = await session.scalar(select(func.count()).select_from(HparamImportanceResult))
        artifact_count = await session.scalar(select(func.count()).select_from(HparamImportanceModelArtifact))

    assert successful == 1
    assert result_count and result_count >= 1
    assert artifact_count == 1
    assert next(iter(storage.uploads)).endswith("/loss/model.joblib")
    await engine.dispose()
