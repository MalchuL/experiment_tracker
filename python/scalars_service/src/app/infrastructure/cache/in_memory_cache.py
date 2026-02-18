from typing import Any
from api.logger import logger
from app.infrastructure.cache.cache import Cache
from datetime import datetime, timedelta
from app.infrastructure.cache.utils.pattern_matcher import PatternMatcher


class InMemoryCache(Cache):
    def __init__(self, ttl_seconds: int):
        self.cache: dict[str, Any] = {}
        self.ttl_seconds = ttl_seconds
        self.timestamps: dict[str, datetime] = {}

    async def get(self, key: str) -> Any | None:
        if key not in self.cache:
            logger.info(f"Cache key {key} not found")
            return None
        if self.timestamps[key] + timedelta(seconds=self.ttl_seconds) < datetime.now():
            del self.cache[key]
            del self.timestamps[key]
            logger.info(f"Cache key {key} expired")
            return None
        logger.info(f"Cache key {key} found")
        return self.cache[key]

    async def set(self, key: str, value: Any) -> None:
        logger.info(f"Setting cache key {key}")
        self.cache[key] = value
        self.timestamps[key] = datetime.now()

    async def remove(self, key: str) -> None:
        del self.cache[key]
        del self.timestamps[key]
        logger.info(f"Removed cache key {key}")

    async def invalidate(self, pattern: str) -> None:
        logger.info(f"Invalidating cache with pattern {pattern}")
        matcher = PatternMatcher()
        for key in list(self.cache.keys()):
            if matcher.matches_redis_pattern(key, pattern):
                del self.cache[key]
                del self.timestamps[key]
                logger.info(f"Invalidated cache key {key}")
