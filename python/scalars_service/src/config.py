from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "ML Metrics Service"
    API_PREFIX: str = "/api"

    # ClickHouse Configuration
    CLICKHOUSE_URL: str = "http://localhost:8123"

    # Redis cache configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    SCALARS_CACHE_TTL_SECONDS: int = 60
    SCALARS_CACHE_MAX_SIZE: int = 1000
    SCALARS_CACHE_ENABLED: bool = True
    SCALARS_MAPPING_TABLE: str = "scalars_mapping_9b1b1a2a9b2a4d3aa1f3e2b9f0b1c2d3"

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
