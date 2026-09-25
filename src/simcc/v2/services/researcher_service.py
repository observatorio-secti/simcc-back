"""Serviço para busca e listagem de pesquisadores v2."""

import math
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories import researcher_repo
from simcc.v2.schemas.filters import ResearcherFilter
from simcc.v2.schemas.params import (
    PaginationParams,
    SearchOptions,
    SortParams,
)
from simcc.v2.schemas.researcher import (
    Meta,
    Pagination,
    SearchResponse,
    Sort,
)
from simcc.v2.services import mv_refresh_service

MAX_MATCHES_PER_PAGE = 50


async def search_researchers(
    session: AsyncSession,
    filters: Optional[ResearcherFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[SortParams] = None,
    options: Optional[SearchOptions] = None,
) -> SearchResponse:
    """Busca pesquisadores com paginação, ordenação e filtros.

    Comportamento de paginação: quando uma página além do total de páginas é
    requisitada, retorna lista vazia com `has_next=False`. `has_prev` é True
    apenas se houver páginas e a página solicitada for a imediatamente
    posterior à última (`page <= total_pages + 1`), sendo False para páginas
    mais distantes ou quando `total_items == 0`.
    """
    start_time = time.perf_counter()
    resolved_filters = filters or ResearcherFilter()
    resolved_pagination = pagination or PaginationParams()
    resolved_sort = sort or SortParams()
    resolved_options = options or SearchOptions()

    # Validações de consistência entre parâmetros
    has_q = bool(resolved_filters.q and resolved_filters.q.strip())
    if resolved_sort.sort_by == 'relevance' and not has_q:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Ordenação 'sort_by=relevance' requer o filtro de busca 'q'."
            ),
        )

    if 'matches' in resolved_options.include:
        if not has_q:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Inclusão 'include=matches' requer o filtro de busca 'q'."
                ),
            )
        if resolved_pagination.per_page > MAX_MATCHES_PER_PAGE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Inclusão 'include=matches' só é permitida "
                    f"com 'per_page <= {MAX_MATCHES_PER_PAGE}'."
                ),
            )

    items, total_items = await researcher_repo.fetch_researchers(
        session=session,
        filters=resolved_filters,
        pagination=resolved_pagination,
        sort=resolved_sort,
    )

    # Inclusão de matches (evidências textuais nos documentos e perfil)
    if 'matches' in resolved_options.include and items:
        page_ids = [r.researcher_id for r in items]
        matches_map = await researcher_repo.fetch_matches(
            session=session,
            page_ids=page_ids,
            q=resolved_filters.q,
            limit=resolved_options.matches_limit,
        )
        for r in items:
            if r.researcher_id in matches_map:
                r.matches = matches_map[r.researcher_id]

    # Cálculo dos facets opt-in
    facets = None
    if resolved_options.facets:
        facets = await researcher_repo.fetch_requested_facets(
            session=session,
            filters=resolved_filters,
            requested_facets=resolved_options.facets,
        )

    took_ms = int((time.perf_counter() - start_time) * 1000)

    if total_items == 0:
        total_pages = 0
        has_next = False
        has_prev = False
    else:
        total_pages = (
            math.ceil(total_items / resolved_pagination.per_page)
            if resolved_pagination.per_page > 0
            else 0
        )
        has_next = resolved_pagination.page < total_pages
        has_prev = (
            resolved_pagination.page > 1
            and resolved_pagination.page <= total_pages + 1
        )

    return SearchResponse(
        data=items,
        pagination=Pagination(
            page=resolved_pagination.page,
            per_page=resolved_pagination.per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        ),
        filters_applied=resolved_filters,
        sort=Sort(
            by=resolved_sort.sort_by,
            order=resolved_sort.sort_order,
        ),
        meta=Meta(
            took_ms=took_ms,
            cached=False,
            timestamp=datetime.now(timezone.utc),
            data_as_of=mv_refresh_service.get_last_refresh_timestamp(),
        ),
        facets=facets,
        summary=None,
    )
