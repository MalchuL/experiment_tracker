from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.domain.scalars.dto import ScalarsPointsResultDTO
from app.infrastructure.cache.cache import Cache


class ScalarsCache(Cache):
    def __init__(
        self,
        redis: Redis,
        ttl_seconds: int,
        max_size: int,
        enabled: bool = True,
        key_prefix: str = "scalars_cache",
    ) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.enabled = enabled and ttl_seconds > 0 and max_size > 0
        self.key_prefix = key_prefix
        self._zset_key = f"{self.key_prefix}:keys"

    def build_key(
        self,
        project_id: UUID,
        experiment_id: UUID,
        max_points: Optional[int],
        return_tags: bool,
    ) -> str:
        max_points_value = "none" if max_points is None else str(max_points)
        return (
            f"{self.key_prefix}:{project_id}:{experiment_id}:"
            f"max_points={max_points_value}:return_tags={int(return_tags)}"
        )

    async def get(self, key: str) -> Optional[ScalarsPointsResultDTO]:
        if not self.enabled:
            return None
        try:
            cached = await self.redis.get(key)
            if cached is None:
                return None
            await self.redis.zadd(self._zset_key, {key: time.time()})
            return ScalarsPointsResultDTO.model_validate_json(cached)
        except RedisError:
            return None

    async def set(self, key: str, value: ScalarsPointsResultDTO) -> None:
        if not self.enabled:
            return
        try:
            payload = value.model_dump_json()
            pipe = self.redis.pipeline()
            pipe.setex(key, self.ttl_seconds, payload)
            pipe.zadd(self._zset_key, {key: time.time()})
            await pipe.execute()
            await self._enforce_max_size()
        except RedisError:
            return

    async def remove(self, key: str) -> None:
        if not self.enabled:
            return
        try:
            pipe = self.redis.pipeline()
            pipe.delete(key)
            pipe.zrem(self._zset_key, key)
            await pipe.execute()
        except RedisError:
            return

    async def invalidate(self, pattern: str) -> None:
        if not self.enabled:
            return
        try:
            keys_to_delete = []
            async for key in self.redis.scan_iter(match=pattern):
                keys_to_delete.append(key)
            if not keys_to_delete:
                return
            pipe = self.redis.pipeline()
            pipe.delete(*keys_to_delete)
            pipe.zrem(self._zset_key, *keys_to_delete)
            await pipe.execute()
        except RedisError:
            return

    async def _enforce_max_size(self) -> None:
        if not self.enabled:
            return
        try:
            total = await self.redis.zcard(self._zset_key)
            if total <= self.max_size:
                return
            excess = total - self.max_size
            keys_to_remove = await self.redis.zrange(self._zset_key, 0, excess - 1)
            if not keys_to_remove:
                return
            pipe = self.redis.pipeline()
            pipe.delete(*keys_to_remove)
            pipe.zrem(self._zset_key, *keys_to_remove)
            await pipe.execute()
        except RedisError:
            return
