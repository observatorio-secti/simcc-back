"""Serviço para busca, listagem e detalhe de artigos científicos v2."""

import math
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories import article_repo
from simcc.v2.schemas.params import Pagination, PaginationParams
from simcc.v2.schemas.production import (
    ArticleDetail,
    ArticleFilter,
    ArticleSearchResponse,
    ArticleSort,
    ArticleSummary,
    MagazineRef,
    ResearcherRef,
)
from simcc.v2.schemas.researcher import Meta


def _row_to_summary(
    row: dict, snippets: Optional[list] = None
) -> ArticleSummary:
    """Converte um registro da MV em ArticleSummary."""
    magazine = None
    if (
        row.get('magazine_name')
        or row.get('issn')
        or row.get('qualis')
        or row.get('jcr')
    ):
        magazine = MagazineRef(
            name=row.get('magazine_name'),
            issn=row.get('issn'),
            qualis=row.get('qualis'),
            jcr=row.get('jcr'),
        )

    platform_authors = [
        ResearcherRef(**author)
        for author in (row.get('platform_authors') or [])
    ]

    return ArticleSummary(
        id=row['canonical_id'],
        title=row['title'],
        year=row.get('year'),
        doi=row.get('doi'),
        magazine=magazine,
        platform_authors=platform_authors,
        citations_count=row.get('citations_count') or 0,
        has_abstract=bool(row.get('has_abstract')),
        has_open_access_pdf=bool(row.get('has_open_access_pdf')),
        matches=snippets,
    )


async def search_articles(
    session: AsyncSession,
    filters: Optional[ArticleFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[ArticleSort] = None,
) -> ArticleSearchResponse:
    """Executa a busca paginada de artigos científicos."""
    t0 = time.perf_counter()

    filters = filters or ArticleFilter()
    pagination = pagination or PaginationParams()
    sort = sort or ArticleSort()

    total_items = await article_repo.count_articles(session, filters)
    rows = await article_repo.search_articles(
        session, filters, sort, pagination
    )

    snippets_map = {}
    if filters.q and rows:
        canonical_ids = [row['canonical_id'] for row in rows]
        snippets_map = await article_repo.get_article_snippets(
            session, canonical_ids, filters.q
        )

    data = [
        _row_to_summary(dict(r), snippets=snippets_map.get(r['canonical_id']))
        for r in rows
    ]

    total_pages = (
        math.ceil(total_items / pagination.per_page) if total_items > 0 else 0
    )
    pagination_meta = Pagination(
        page=pagination.page,
        per_page=pagination.per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=pagination.page < total_pages,
        has_prev=pagination.page > 1,
    )

    took_ms = int((time.perf_counter() - t0) * 1000)
    meta = Meta(
        took_ms=took_ms,
        cached=False,
        timestamp=datetime.now(timezone.utc),
    )

    return ArticleSearchResponse(
        data=data,
        pagination=pagination_meta,
        filters_applied=filters,
        sort=sort,
        meta=meta,
    )


async def get_article_detail(
    session: AsyncSession,
    article_id: UUID | str,
) -> ArticleDetail:
    """Recupera o dossiê completo de um artigo por ID canônico ou DOI."""
    row = await article_repo.get_article_by_id(session, article_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artigo '{article_id}' não encontrado",
        )

    row_dict = dict(row)
    base_summary = _row_to_summary(row_dict)

    return ArticleDetail(
        **base_summary.model_dump(),
        abstract=row_dict.get('abstract'),
        landing_page_url=row_dict.get('landing_page_url'),
        pdf_url=row_dict.get('pdf_url'),
        keywords=row_dict.get('keywords'),
        all_authors_raw=row_dict.get('all_authors_raw'),
        language=row_dict.get('language'),
    )
