from app.infrastructure.cache.cache import Cache
from app.infrastructure.cache.in_memory_cache import InMemoryCache


_CACHE = InMemoryCache(ttl_seconds=60)


# TODO: Implement cache factory
async def get_cache() -> Cache:
    return _CACHE
