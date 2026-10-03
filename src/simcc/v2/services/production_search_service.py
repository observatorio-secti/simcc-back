"""Facets e cache comuns às listagens de produção v2."""

import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Optional, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories import production_facets_repo
from simcc.v2.schemas.params import PaginationParams
from simcc.v2.schemas.production import ProductionBaseFilter, ProductionOptions
from simcc.v2.schemas.researcher import Meta
from simcc.v2.services import mv_refresh_service
from simcc.v2.services.search_cache import SearchCache

ResponseT = TypeVar('ResponseT', bound=BaseModel)


async def search_production(  # noqa: PLR0913
    search: Callable[..., Awaitable[ResponseT]],
    response_model: type[ResponseT],
    table: Table,
    *,
    session: AsyncSession,
    filters: ProductionBaseFilter,
    pagination: PaginationParams,
    sort: BaseModel,
    options: Optional[ProductionOptions] = None,
    cache: Optional[SearchCache] = None,
) -> ResponseT:
    """Executa `search` (listagem de um tipo de produção sobre `table`) e
    acrescenta os facets pedidos.

    Com `cache`, a resposta é reaproveitada até o próximo refresh das MVs
    (ver `search_cache`). Validações sempre rodam antes da consulta ao cache.
    """
    start_time = time.perf_counter()
    options = options or ProductionOptions()

    allowed = production_facets_repo.allowed_facets(filters)
    invalid = [facet for facet in options.facets if facet not in allowed]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f'Facets desconhecidos: {invalid}. Permitidos: {allowed}',
        )

    cache_key = None
    if cache is not None:
        cache_key = await cache.build_key(
            f'production_search:{table.name}',
            {
                'filters': _sort_lists(filters.model_dump(mode='json')),
                'pagination': pagination.model_dump(mode='json'),
                'sort': sort.model_dump(mode='json'),
                'options': _sort_lists(options.model_dump(mode='json')),
            },
        )
    if cache_key is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return response_model.model_validate({
                **cached,
                'filters_applied': filters,
                'meta': _build_meta(start_time, cached=True),
            })

    response = await search(
        session=session, filters=filters, pagination=pagination, sort=sort
    )
    if options.facets:
        response.facets = await production_facets_repo.fetch_requested_facets(
            session=session,
            table=table,
            filters=filters,
            requested_facets=options.facets,
            limit=options.facet_limit,
        )
    response.meta = _build_meta(start_time, cached=False)

    if cache_key is not None:
        await cache.set(
            cache_key,
            response.model_dump(
                mode='json', exclude={'meta', 'filters_applied'}
            ),
        )
    return response


def _sort_lists(dump: dict) -> dict:
    return {
        key: sorted(value) if isinstance(value, list) else value
        for key, value in dump.items()
    }


def _build_meta(start_time: float, cached: bool) -> Meta:
    return Meta(
        took_ms=int((time.perf_counter() - start_time) * 1000),
        cached=cached,
        timestamp=datetime.now(timezone.utc),
        data_as_of=mv_refresh_service.get_last_refresh_timestamp(),
    )
