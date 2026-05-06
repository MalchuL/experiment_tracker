from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    api_prefix: str = "/api"
    database_url: str = "sqlite+aiosqlite:///./data.db"
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION-SECRET-KEY-12345"
    app_name: str = "Experiment Tracker"
    allowed_origins: str = "*"
    scalars_service_url: str = "http://127.0.0.1:8001/api"
    object_storage_service_url: str = "http://127.0.0.1:8010/api"
    log_level: str = "INFO"
    log_stacktrace: bool = True
    #: Shared secret for HTTP admin routes (header ``X-Admin-Key``). Env: ``ADMIN_PANEL_KEY``.
    admin_panel_key: str = Field(default="admin")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
