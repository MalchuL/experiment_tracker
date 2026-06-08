"""Load environment-driven configuration for API, worker, ML, and storage."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from mltools.domain.hparam_importance.settings import HparamImportanceSettings


class Settings(BaseSettings):
    """Complete process configuration loaded from environment variables.

    Result:
        Settings instance containing API, database, queue, backend-client, object
        storage, preprocessing, and Random Forest configuration.
    """
    model_config = SettingsConfigDict(env_prefix="", env_file=".env")

    app_name: str = "Experiment Tracker MLTools"
    api_prefix: str = "/internal/mltools"
    database_url: str = "sqlite+aiosqlite:///./mltools.db"
    log_level: str = "INFO"

    backend_base_url: str = "http://127.0.0.1:8000"
    backend_api_token: str = ""
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_broker_url: str = "redis://127.0.0.1:6379/0"
    celery_result_backend: str = "redis://127.0.0.1:6379/1"

    object_storage_endpoint: str | None = None
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None
    object_storage_bucket: str = "mltools"
    object_storage_region: str = "us-east-1"

    hparam_path_separator: str = "<sep>"
    default_array_strategy: str = "skip"
    default_text_strategy: str = "disabled"
    max_category_cardinality: int = 50
    missing_value_strategy: str = "impute"
    min_experiments_per_metric: int = 10

    rf_n_estimators: int = 300
    rf_max_depth: int | None = None
    rf_min_samples_split: int = 2
    rf_min_samples_leaf: int = 1
    rf_random_state: int = 42
    rf_n_jobs: int = -1
    rf_test_size: float = 0.2
    rf_importance_method: str = "impurity"

    def hparam_importance_settings(self) -> HparamImportanceSettings:
        """Map infrastructure configuration into the domain settings value object.

        Returns:
            HparamImportanceSettings: Immutable settings consumed by the
            hyperparameter-importance bounded context without coupling it to
            Pydantic or environment loading.
        """
        return HparamImportanceSettings(
            hparam_path_separator=self.hparam_path_separator,
            default_array_strategy=self.default_array_strategy,
            default_text_strategy=self.default_text_strategy,
            max_category_cardinality=self.max_category_cardinality,
            missing_value_strategy=self.missing_value_strategy,
            min_experiments_per_metric=self.min_experiments_per_metric,
            rf_n_estimators=self.rf_n_estimators,
            rf_max_depth=self.rf_max_depth,
            rf_min_samples_split=self.rf_min_samples_split,
            rf_min_samples_leaf=self.rf_min_samples_leaf,
            rf_random_state=self.rf_random_state,
            rf_n_jobs=self.rf_n_jobs,
            rf_test_size=self.rf_test_size,
            rf_importance_method=self.rf_importance_method,
            object_storage_bucket=self.object_storage_bucket,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache process configuration.

    Returns:
        Settings: Singleton environment-derived configuration instance.
    """
    return Settings()
"""Environment-backed configuration for the MLTools API and worker processes."""
