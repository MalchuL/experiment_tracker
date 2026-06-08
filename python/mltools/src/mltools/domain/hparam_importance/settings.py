"""Define immutable analysis settings consumed by domain services."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HparamImportanceSettings:
    """Domain configuration for dataset processing and Random Forest training.

    Result:
        Immutable value object containing only settings needed by the bounded
        context, independent of environment-loading infrastructure.
    """
    hparam_path_separator: str
    default_array_strategy: str
    default_text_strategy: str
    max_category_cardinality: int
    missing_value_strategy: str
    min_experiments_per_metric: int
    rf_n_estimators: int
    rf_max_depth: int | None
    rf_min_samples_split: int
    rf_min_samples_leaf: int
    rf_random_state: int
    rf_n_jobs: int
    rf_test_size: float
    rf_importance_method: str
    object_storage_bucket: str
"""Immutable configuration values used by hyperparameter importance analysis."""
