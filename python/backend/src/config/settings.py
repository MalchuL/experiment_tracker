from functools import lru_cache
from pydantic_settings import BaseSettings

from pprint import pprint


class Settings(BaseSettings):
    api_prefix: str = "/api"
    database_url: str = "sqlite+aiosqlite:///./data.db"
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION-SECRET-KEY-12345"
    app_name: str = "Experiment Tracker"
    allowed_origins: str = "*"
    scalars_service_url: str = "http://127.0.0.1:8001/api"

    class Config:
        env_prefix = ""
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


pprint(get_settings().model_dump())
