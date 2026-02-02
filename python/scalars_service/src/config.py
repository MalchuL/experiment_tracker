from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "ML Metrics Service"
    API_PREFIX: str = "/api"

    # QuestDB Configuration
    QUEST_DB_URL: str = "localhost:9009"

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
