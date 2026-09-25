"""Dependências compartilhadas dos endpoints v2."""

from typing import Annotated

from fastapi import Depends

from simcc.core.cache import get_redis_client
from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings
from simcc.v2.services.search_cache import SearchCache


def get_search_cache(
    settings: Settings = Depends(get_settings),
) -> SearchCache:
    if not settings.REDIS_ENABLED:
        return SearchCache(redis_client=None, ttl=settings.V2_SEARCH_CACHE_TTL)
    return SearchCache(
        redis_client=get_redis_client(settings.REDIS_URL),
        ttl=settings.V2_SEARCH_CACHE_TTL,
    )


SearchCacheDep = Annotated[SearchCache, Depends(get_search_cache)]
