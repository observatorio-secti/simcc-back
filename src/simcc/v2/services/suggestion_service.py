"""Serviço para sugestão de termos v2."""

import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories import suggestion_repo
from simcc.v2.schemas.researcher import Meta
from simcc.v2.schemas.suggestion import SuggestionParams, SuggestionResponse
from simcc.v2.services import mv_refresh_service
from simcc.v2.services.search_cache import SearchCache


async def suggest_terms(
    session: AsyncSession,
    params: SuggestionParams,
    *,
    cache: Optional[SearchCache] = None,
) -> SuggestionResponse:
    """Sugere termos do dicionário que começam com `params.q`.

    Com `cache`, a resposta é reaproveitada até a próxima invalidação do
    cache de busca (ver `search_cache`), que ocorre após a carga que
    reconstrói o dicionário.
    """
    start_time = time.perf_counter()

    cache_key = None
    if cache is not None:
        cache_key = await cache.build_key(
            'suggestion',
            {
                'q': params.q.lower(),
                'source_type': sorted(params.source_type),
                'limit': params.limit,
            },
        )
    if cache_key is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return SuggestionResponse.model_validate({
                **cached,
                'meta': _build_meta(start_time, cached=True),
            })

    data = await suggestion_repo.fetch_suggestions(
        session=session,
        q=params.q,
        source_types=params.source_type,
        limit=params.limit,
    )
    response = SuggestionResponse(
        data=data, meta=_build_meta(start_time, cached=False)
    )

    if cache_key is not None:
        await cache.set(
            cache_key, response.model_dump(mode='json', exclude={'meta'})
        )
    return response


def _build_meta(start_time: float, cached: bool) -> Meta:
    return Meta(
        took_ms=int((time.perf_counter() - start_time) * 1000),
        cached=cached,
        timestamp=datetime.now(timezone.utc),
        data_as_of=mv_refresh_service.get_last_refresh_timestamp(),
    )
