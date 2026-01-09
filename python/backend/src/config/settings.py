from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_prefix: str = "/api"
    database_url: str = "sqlite+aiosqlite:///./data.db"
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION-SECRET-KEY-12345"
    app_name: str = "Experiment Tracker"

    class Config:
        env_prefix = ""
        env_file = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
