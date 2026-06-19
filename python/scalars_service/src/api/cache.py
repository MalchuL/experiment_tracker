from app.infrastructure.cache.cache import Cache
from app.infrastructure.cache.in_memory_cache import InMemoryCache
from config import get_settings


_CACHE = InMemoryCache(ttl_seconds=get_settings().SCALARS_CACHE_TTL_SECONDS)


# TODO: Implement cache factory
async def get_cache() -> Cache:
    return _CACHE
