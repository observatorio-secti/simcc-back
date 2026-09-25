"""Dependências compartilhadas dos endpoints v2."""

from typing import Annotated

from fastapi import Depends

from simcc.core.cache import get_redis_client
from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.params import PaginationParams, SearchOptions, SortParams
from simcc.v2.schemas.query import as_query
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

# Parâmetros de query declarados pelos próprios models (ver `as_query`)
ResearcherFilterDep = Annotated[
    ResearcherFilter, Depends(as_query(ResearcherFilter))
]
PaginationDep = Annotated[
    PaginationParams, Depends(as_query(PaginationParams))
]
SortDep = Annotated[SortParams, Depends(as_query(SortParams))]
SearchOptionsDep = Annotated[SearchOptions, Depends(as_query(SearchOptions))]
