"""Build datasets, train regressors, and persist hparam importance outputs."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Any
from uuid import UUID

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy.ext.asyncio import AsyncSession

from mltools.domain.hparam_importance.dto import TargetMetricDTO
from mltools.db.models import (
    HparamImportanceJob,
    HparamImportanceJobExperiment,
    HparamImportanceJobMessage,
    HparamImportanceJobMetricExperiment,
    HparamImportanceJobParameter,
    HparamImportanceModelArtifact,
    HparamImportanceResult,
)
from mltools.clients.object_storage.client import model_artifact_key
from mltools.domain.hparam_importance.protocol import (
    BackendDataClientProtocol,
    ModelStorageProtocol,
)
from mltools.domain.hparam_importance.settings import HparamImportanceSettings

SUSPICIOUS_TOKENS = {
    "name", "path", "dir", "file", "uuid", "id", "hash", "commit", "created_at",
    "updated_at", "finished_at", "result", "metric", "score", "loss", "accuracy",
    "best", "final", "checkpoint",
}


@dataclass
class WarningItem:
    """In-memory diagnostic emitted while building or training an analysis.

    Result:
        Structured diagnostic ready to persist as a job message.
    """
    category: str
    message: str
    experiment_id: UUID | None = None
    flat_key: str | None = None
    target_metric: dict[str, Any] | None = None
    level: str = "warning"


@dataclass
class FlatDocument:
    """Flattened representation of one experiment's nested hparams.

    Result:
        Values keyed by escaped flat keys, canonical reverse paths, and diagnostics.
    """
    values: dict[str, Any] = field(default_factory=dict)
    paths: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[WarningItem] = field(default_factory=list)


def escape_path_part(part: str, separator: str) -> tuple[str, bool]:
    """Escape one JSON path component for a flattened key.

    Args:
        part: Original JSON object key.
        separator: Configured flat-key path separator.

    Returns:
        tuple[str, bool]: Escaped component and whether a separator collision occurred.
    """
    escaped = part.replace("\\", "\\\\")
    collision = separator in escaped
    return escaped.replace(separator, f"\\{separator}"), collision


def flat_key(path: list[str], separator: str) -> tuple[str, bool]:
    """Build an escaped flattened key from a canonical path.

    Args:
        path: Original JSON path components.
        separator: Configured separator inserted between escaped components.

    Returns:
        tuple[str, bool]: Flattened key and whether any component contained the
        separator.
    """
    escaped = [escape_path_part(part, separator) for part in path]
    return separator.join(item[0] for item in escaped), any(item[1] for item in escaped)


def flatten_hparams(
    payload: dict[str, Any],
    *,
    separator: str = "<sep>",
    default_array_strategy: str = "skip",
    overrides: dict[str, dict[str, Any]] | None = None,
) -> FlatDocument:
    """Flatten one nested hparams object using configured array behavior.

    Args:
        payload: Top-level nested hyperparameter object.
        separator: Separator used between escaped path components.
        default_array_strategy: Default handling for arrays without an override.
        overrides: Per-flat-key processing overrides.

    Returns:
        FlatDocument: Flattened scalar/category values, canonical reverse paths, and
        non-fatal diagnostics.
    """
    result = FlatDocument()
    overrides = overrides or {}

    def visit(value: Any, path: list[str]) -> None:
        """Recursively visit one nested hparams value.

        Args:
            value: Current JSON-native value.
            path: Canonical path from the hparams root to ``value``.

        Returns:
            None: Mutates the enclosing ``FlatDocument`` accumulator.
        """
        key, collision = flat_key(path, separator)
        override = overrides.get(key, {})
        if collision:
            result.warnings.append(
                WarningItem("path_separator_collision", f"Escaped separator in {path!r}", flat_key=key)
            )
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, [*path, child_key])
            return
        if isinstance(value, list):
            strategy = override.get("array_strategy", default_array_strategy)
            if strategy == "flatten_by_index":
                for index, child in enumerate(value):
                    visit(child, [*path, str(index)])
                return
            if strategy == "stringify_category":
                value = json.dumps(value, sort_keys=True, separators=(",", ":"))
            else:
                result.warnings.append(
                    WarningItem("unsupported_array", f"Array parameter {key} was skipped", flat_key=key)
                )
                return
        result.values[key] = value
        result.paths[key] = path

    for root_key, value in payload.items():
        visit(value, [root_key])
    return result


def infer_type(values: list[Any]) -> str:
    """Infer a deterministic parameter type from observed experiment values.

    Args:
        values: Values for one flattened parameter across experiments.

    Returns:
        str: One of ``number``, ``boolean``, ``date``, ``datetime``, ``category``,
        ``text``, or ``unknown``.
    """
    present = [value for value in values if value is not None]
    if not present:
        return "unknown"
    if all(isinstance(value, bool) for value in present):
        return "boolean"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in present):
        return "number"
    if all(isinstance(value, str) for value in present):
        date_values = []
        datetime_values = []
        for value in present:
            try:
                date_values.append(date.fromisoformat(value))
            except ValueError:
                pass
            try:
                datetime_values.append(datetime.fromisoformat(value.replace("Z", "+00:00")))
            except ValueError:
                pass
        if len(date_values) == len(present) and all("T" not in value for value in present):
            return "date"
        if len(datetime_values) == len(present):
            return "datetime"
        return "category" if max(map(len, present)) <= 256 else "text"
    return "unknown"


def default_processing(
    selected_type: str, unique_count: int, settings: HparamImportanceSettings
) -> str:
    """Select the default preprocessing strategy for an inferred/selected type.

    Args:
        selected_type: Effective parameter type after overrides.
        unique_count: Number of unique non-missing observed values.
        settings: Domain analysis settings.

    Returns:
        str: Default strategy, disabling unsupported or high-cardinality parameters.
    """
    if selected_type == "number":
        return "raw"
    if selected_type == "boolean":
        return "as_int"
    if selected_type in {"date", "datetime"}:
        return "timestamp"
    if selected_type == "category":
        return "disabled" if unique_count > settings.max_category_cardinality else "one_hot"
    return settings.default_text_strategy if selected_type == "text" else "disabled"


def convert_value(value: Any, selected_type: str, strategy: str) -> Any:
    """Convert one raw hparam value into a model-input value.

    Args:
        value: Raw JSON-native parameter value or ``None``.
        selected_type: Effective parameter type.
        strategy: Selected preprocessing strategy.

    Returns:
        Any: Numeric, string, or ``NaN`` value suitable for a pandas data frame.

    Raises:
        ValueError: If date, datetime, or numeric conversion fails.
        TypeError: If the input cannot be converted to the selected type.
    """
    if value is None:
        return np.nan
    if selected_type == "number":
        converted = float(value)
        if strategy == "log":
            return math.log(converted) if converted > 0 else np.nan
        return converted
    if selected_type == "boolean":
        return int(bool(value))
    if selected_type in {"date", "datetime"}:
        parsed = (
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if selected_type == "datetime"
            else datetime.combine(date.fromisoformat(str(value)), datetime.min.time())
        )
        return parsed.timestamp()
    return str(value)


def build_transformer(metadata: list[dict[str, Any]]) -> ColumnTransformer:
    """Build the sklearn preprocessing graph for included parameters.

    Args:
        metadata: Parameter metadata containing selected types, strategies, and
        inclusion state.

    Returns:
        ColumnTransformer: Transformer that imputes numeric values and one-hot
        encodes categorical values.
    """
    transformers = []
    for index, item in enumerate(metadata):
        strategy = item["processing_strategy"]
        if not item["included"]:
            continue
        if item["selected_type"] in {"number", "boolean", "date", "datetime"}:
            steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
            if strategy == "standardize":
                steps.append(("scale", StandardScaler()))
            transformer = Pipeline(steps)
        else:
            transformer = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("one_hot", OneHotEncoder(handle_unknown="ignore")),
                ]
            )
        transformers.append((f"f{index}", transformer, [item["flat_key"]]))
    return ColumnTransformer(transformers, remainder="drop", verbose_feature_names_out=False)


def aggregate_importance(
    transformer: ColumnTransformer, importances: np.ndarray, metadata: list[dict[str, Any]]
) -> dict[str, float]:
    """Aggregate transformed feature importances back to original hparams.

    Args:
        transformer: Fitted column transformer exposing output slices.
        importances: Random Forest importance per transformed feature column.
        metadata: Original parameter metadata in transformer construction order.

    Returns:
        dict[str, float]: Summed importance keyed by original flattened hparam.
    """
    totals: dict[str, float] = {}
    for index, item in enumerate(metadata):
        name = f"f{index}"
        if name not in transformer.output_indices_:
            continue
        output_slice = transformer.output_indices_[name]
        totals[item["flat_key"]] = float(importances[output_slice].sum())
    return totals


async def run_analysis(
    session: AsyncSession,
    job: HparamImportanceJob,
    *,
    backend: BackendDataClientProtocol,
    storage: ModelStorageProtocol,
    settings: HparamImportanceSettings,
) -> int:
    """Build datasets, train per-metric models, and persist analysis outputs.

    Args:
        session: Worker-owned async SQLAlchemy session.
        job: Persisted running job containing targets and immutable configuration.
        backend: Port for fetching project experiments, hparams, and metric targets.
        storage: Port for uploading serialized trained-model artifacts.
        settings: Immutable domain preprocessing and Random Forest settings.

    Returns:
        int: Number of target metrics successfully trained and persisted.

    Raises:
        Exception: Critical backend, database, training, serialization, or storage
        failures propagate to the worker so it can mark the job failed. Individual
        parameter conversion and missing-data problems are persisted as warnings.
    """
    targets = [TargetMetricDTO.model_validate(item) for item in job.target_metrics]
    excluded_experiments = {UUID(item) for item in job.config["excluded_experiment_ids"]}
    excluded_hparams = set(job.config["excluded_hparams"])
    overrides = job.config["parameter_overrides"]

    experiments = await backend.list_experiments(job.project_id)
    job.stage = "fetching_hparams"
    job.progress = 0.15
    await session.commit()
    documents: dict[UUID, FlatDocument] = {}
    all_keys: set[str] = set()
    paths: dict[str, list[str]] = {}
    warnings: list[WarningItem] = []
    for experiment in experiments:
        experiment_id = UUID(experiment["id"])
        excluded = experiment_id in excluded_experiments
        hparams = None if excluded else await backend.get_hparams(experiment_id)
        session.add(
            HparamImportanceJobExperiment(
                job_id=job.id,
                experiment_id=experiment_id,
                experiment_name=experiment["name"],
                included=not excluded and hparams is not None,
                exclude_reason="excluded_by_user" if excluded else ("missing_hparams" if hparams is None else None),
                has_hparams=hparams is not None,
            )
        )
        if excluded:
            warnings.append(WarningItem("excluded_experiment", f"Experiment {experiment['name']} was excluded", experiment_id))
            continue
        if hparams is None:
            warnings.append(WarningItem("missing_hparams", f"Experiment {experiment['name']} has no hparams", experiment_id))
            continue
        document = flatten_hparams(
            hparams,
            separator=settings.hparam_path_separator,
            default_array_strategy=settings.default_array_strategy,
            overrides=overrides,
        )
        documents[experiment_id] = document
        all_keys.update(document.values)
        paths.update(document.paths)
        warnings.extend(document.warnings)

    job.stage = "inferring_types"
    job.progress = 0.4
    await session.commit()
    metadata: list[dict[str, Any]] = []
    for key in sorted(all_keys):
        values = [document.values.get(key) for document in documents.values()]
        inferred = infer_type(values)
        override = overrides.get(key, {})
        selected = override.get("selected_type", inferred)
        unique_count = len({json.dumps(value, sort_keys=True) for value in values if value is not None})
        strategy = override.get("processing_strategy") or default_processing(selected, unique_count, settings)
        included = key not in excluded_hparams and strategy != "disabled"
        warning_count = 0
        if any(token in paths[key][-1].lower() for token in SUSPICIOUS_TOKENS):
            warnings.append(WarningItem("suspicious_parameter_name", f"Parameter {key} may leak run identity or results", flat_key=key))
            warning_count += 1
        if selected == "category" and unique_count > settings.max_category_cardinality:
            included = False
            warnings.append(WarningItem("high_cardinality_category", f"Parameter {key} exceeds category cardinality limit", flat_key=key))
            warning_count += 1
        if unique_count <= 1:
            included = False
            warnings.append(WarningItem("constant_feature", f"Parameter {key} is constant", flat_key=key))
            warning_count += 1
        item = {
            "flat_key": key,
            "path": paths[key],
            "inferred_type": inferred,
            "selected_type": selected,
            "processing_strategy": strategy,
            "array_strategy": override.get("array_strategy"),
            "included": included,
            "exclude_reason": "excluded_by_user" if key in excluded_hparams else (None if included else strategy),
            "missing_count": sum(value is None for value in values),
            "unique_count": unique_count,
            "error_count": 0,
            "warning_count": warning_count,
        }
        metadata.append(item)
        session.add(HparamImportanceJobParameter(job_id=job.id, **item))

    job.stage = "fetching_metrics"
    job.progress = 0.5
    await session.commit()
    metric_values = await backend.get_aggregated_metrics(job.project_id, targets)
    successful = 0
    for target_index, target in enumerate(targets):
        job.stage = "training_models"
        job.progress = 0.6 + (0.3 * target_index / max(len(targets), 1))
        await session.commit()
        target_dict = target.model_dump()
        values = metric_values[(target.name, target.label)]
        rows: list[dict[str, Any]] = []
        y: list[float] = []
        for experiment in experiments:
            experiment_id = UUID(experiment["id"])
            usable = experiment_id in documents and experiment_id in values
            reason = None if usable else ("metric_missing" if experiment_id in documents else "not_in_dataset")
            session.add(
                HparamImportanceJobMetricExperiment(
                    job_id=job.id,
                    target_metric=target_dict,
                    experiment_id=experiment_id,
                    used=usable,
                    skip_reason=reason,
                    target_value=values.get(experiment_id),
                    target_value_strategy="project_configured",
                )
            )
            if usable:
                converted: dict[str, Any] = {}
                for item in metadata:
                    value = documents[experiment_id].values.get(item["flat_key"])
                    try:
                        converted[item["flat_key"]] = convert_value(
                            value, item["selected_type"], item["processing_strategy"]
                        )
                    except (TypeError, ValueError, OverflowError):
                        converted[item["flat_key"]] = np.nan
                        warnings.append(WarningItem("conversion_failed", f"Could not convert {item['flat_key']}", experiment_id, item["flat_key"], target_dict))
                rows.append(converted)
                y.append(values[experiment_id])
            elif experiment_id in documents:
                warnings.append(WarningItem("metric_missing", f"Metric {target.name} is missing for experiment {experiment['name']}", experiment_id, target_metric=target_dict))
        if len(rows) < settings.min_experiments_per_metric:
            warnings.append(WarningItem("insufficient_data", f"Metric {target.name} has only {len(rows)} usable experiments", target_metric=target_dict))
            continue
        active_metadata = [item for item in metadata if item["included"]]
        if not active_metadata:
            warnings.append(WarningItem("training_failed", f"Metric {target.name} has no usable parameters", target_metric=target_dict))
            continue
        x = pd.DataFrame(rows)
        transformer = build_transformer(metadata)
        model = RandomForestRegressor(
            n_estimators=settings.rf_n_estimators,
            max_depth=settings.rf_max_depth,
            min_samples_split=settings.rf_min_samples_split,
            min_samples_leaf=settings.rf_min_samples_leaf,
            random_state=settings.rf_random_state,
            n_jobs=settings.rf_n_jobs,
        )
        pipeline = Pipeline([("preprocess", transformer), ("model", model)])
        validation_rows = 0
        score = None
        if len(rows) >= max(settings.min_experiments_per_metric, 5) and 0 < settings.rf_test_size < 1:
            x_train, x_validation, y_train, y_validation = train_test_split(
                x, y, test_size=settings.rf_test_size, random_state=settings.rf_random_state
            )
            pipeline.fit(x_train, y_train)
            validation_rows = len(x_validation)
            if validation_rows >= 2:
                score = float(r2_score(y_validation, pipeline.predict(x_validation)))
        else:
            x_train, y_train = x, y
            pipeline.fit(x_train, y_train)
        fitted_transformer: ColumnTransformer = pipeline.named_steps["preprocess"]
        fitted_model: RandomForestRegressor = pipeline.named_steps["model"]
        importance = aggregate_importance(fitted_transformer, fitted_model.feature_importances_, metadata)
        ranked = sorted(importance.items(), key=lambda item: (-item[1], item[0]))
        for rank, (key, value) in enumerate(ranked, start=1):
            session.add(
                HparamImportanceResult(
                    job_id=job.id,
                    target_metric=target_dict,
                    flat_key=key,
                    path=paths[key],
                    importance=value,
                    rank=rank,
                    importance_method=settings.rf_importance_method,
                )
            )
        artifact = {
            "pipeline": pipeline,
            "feature_mapping": paths,
            "parameter_metadata": metadata,
            "target_metric": target_dict,
            "job_config": job.config,
            "versions": {"sklearn": sklearn.__version__, "pandas": pd.__version__},
        }
        buffer = BytesIO()
        joblib.dump(artifact, buffer)
        key = model_artifact_key(str(job.project_id), str(job.id), target.name, target.label)
        storage.upload(key, buffer.getvalue())
        job.stage = "saving_results"
        job.progress = 0.9 + (0.08 * (target_index + 1) / max(len(targets), 1))
        session.add(
            HparamImportanceModelArtifact(
                job_id=job.id,
                target_metric=target_dict,
                model_type="RandomForestRegressor",
                object_storage_bucket=settings.object_storage_bucket,
                object_storage_key=key,
                artifact_format="joblib",
                train_rows=len(x_train),
                validation_rows=validation_rows,
                feature_count=len(importance),
                score_name="r2" if score is not None else None,
                score_value=score,
            )
        )
        successful += 1

    for warning in warnings:
        session.add(
            HparamImportanceJobMessage(
                job_id=job.id,
                level=warning.level,
                category=warning.category,
                message=warning.message,
                experiment_id=warning.experiment_id,
                flat_key=warning.flat_key,
                target_metric=warning.target_metric,
            )
        )
    await session.flush()
    return successful
"""Dataset construction, preprocessing, training, and persistence for importance jobs."""
