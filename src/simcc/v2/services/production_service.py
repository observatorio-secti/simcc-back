"""Serviço para busca, listagem e detalhe de produções canônicas.
Livros, Capítulos, Software, Patentes e Eventos.
"""

import math
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.v2.repositories import production_repo
from simcc.v2.repositories.search_tables import (
    mv_canonical_book_chapters,
    mv_canonical_books,
    mv_canonical_events,
    mv_canonical_patents,
    mv_canonical_software,
)
from simcc.v2.schemas.params import Pagination, PaginationParams
from simcc.v2.schemas.production import (
    BookChapterDetail,
    BookChapterFilter,
    BookChapterSearchResponse,
    BookChapterSummary,
    BookDetail,
    BookFilter,
    BookSearchResponse,
    BookSummary,
    EventDetail,
    EventFilter,
    EventSearchResponse,
    EventSummary,
    PatentDetail,
    PatentFilter,
    PatentSearchResponse,
    PatentSummary,
    ProductionSort,
    ResearcherRef,
    SoftwareDetail,
    SoftwareFilter,
    SoftwareSearchResponse,
    SoftwareSummary,
)
from simcc.v2.schemas.researcher import Meta


def _authors(row: dict) -> list[ResearcherRef]:
    return [
        ResearcherRef(**a) for a in (row.get('platform_authors') or [])
    ]


# =========================================================================
# 1. LIVROS
# =========================================================================

async def search_books(
    session: AsyncSession,
    filters: Optional[BookFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[ProductionSort] = None,
) -> BookSearchResponse:
    t0 = time.perf_counter()
    filters = filters or BookFilter()
    pagination = pagination or PaginationParams()
    sort = sort or ProductionSort()

    table = mv_canonical_books
    total = await production_repo.count_production(session, table, filters)
    rows = await production_repo.search_production(
        session, table, filters, sort, pagination
    )

    snippets = {}
    if filters.q and rows:
        ids = [r['canonical_id'] for r in rows]
        snippets = await production_repo.get_production_snippets(
            session, table, ids, filters.q, secondary_col='publishing_company'
        )

    data = [
        BookSummary(
            id=r['canonical_id'],
            title=r['title'],
            year=r.get('year'),
            isbn=r.get('isbn'),
            publishing_company=r.get('publishing_company'),
            platform_authors=_authors(dict(r)),
            matches=snippets.get(r['canonical_id']),
        )
        for r in rows
    ]

    total_pages = math.ceil(total / pagination.per_page) if total > 0 else 0
    return BookSearchResponse(
        data=data,
        pagination=Pagination(
            page=pagination.page,
            per_page=pagination.per_page,
            total_items=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_prev=pagination.page > 1,
        ),
        filters_applied=filters,
        sort=sort,
        meta=Meta(
            took_ms=int((time.perf_counter() - t0) * 1000),
            cached=False,
            timestamp=datetime.now(timezone.utc),
        ),
    )


async def get_book_detail(
    session: AsyncSession,
    book_id: UUID | str,
) -> BookDetail:
    row = await production_repo.get_production_by_id(
        session, mv_canonical_books, book_id, natural_key_col='isbn'
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livro '{book_id}' não encontrado",
        )
    r = dict(row)
    return BookDetail(
        id=r['canonical_id'],
        title=r['title'],
        year=r.get('year'),
        isbn=r.get('isbn'),
        publishing_company=r.get('publishing_company'),
        platform_authors=_authors(r),
        doi=r.get('doi'),
        publishing_company_city=r.get('publishing_company_city'),
        all_authors_raw=r.get('all_authors_raw'),
    )


# =========================================================================
# 2. CAPÍTULOS DE LIVROS
# =========================================================================

async def search_book_chapters(
    session: AsyncSession,
    filters: Optional[BookChapterFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[ProductionSort] = None,
) -> BookChapterSearchResponse:
    t0 = time.perf_counter()
    filters = filters or BookChapterFilter()
    pagination = pagination or PaginationParams()
    sort = sort or ProductionSort()

    table = mv_canonical_book_chapters
    total = await production_repo.count_production(session, table, filters)
    rows = await production_repo.search_production(
        session, table, filters, sort, pagination
    )

    snippets = {}
    if filters.q and rows:
        ids = [r['canonical_id'] for r in rows]
        snippets = await production_repo.get_production_snippets(
            session, table, ids, filters.q, secondary_col='book_title'
        )

    data = [
        BookChapterSummary(
            id=r['canonical_id'],
            title=r['title'],
            book_title=r.get('book_title'),
            year=r.get('year'),
            isbn=r.get('isbn'),
            publishing_company=r.get('publishing_company'),
            platform_authors=_authors(dict(r)),
            matches=snippets.get(r['canonical_id']),
        )
        for r in rows
    ]

    total_pages = math.ceil(total / pagination.per_page) if total > 0 else 0
    return BookChapterSearchResponse(
        data=data,
        pagination=Pagination(
            page=pagination.page,
            per_page=pagination.per_page,
            total_items=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_prev=pagination.page > 1,
        ),
        filters_applied=filters,
        sort=sort,
        meta=Meta(
            took_ms=int((time.perf_counter() - t0) * 1000),
            cached=False,
            timestamp=datetime.now(timezone.utc),
        ),
    )


async def get_book_chapter_detail(
    session: AsyncSession,
    chapter_id: UUID | str,
) -> BookChapterDetail:
    row = await production_repo.get_production_by_id(
        session, mv_canonical_book_chapters, chapter_id, natural_key_col='isbn'
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capítulo '{chapter_id}' não encontrado",
        )
    r = dict(row)
    return BookChapterDetail(
        id=r['canonical_id'],
        title=r['title'],
        book_title=r.get('book_title'),
        year=r.get('year'),
        isbn=r.get('isbn'),
        publishing_company=r.get('publishing_company'),
        platform_authors=_authors(r),
        doi=r.get('doi'),
        organizers=r.get('organizers'),
        start_page=r.get('start_page'),
        end_page=r.get('end_page'),
        all_authors_raw=r.get('all_authors_raw'),
    )


# =========================================================================
# 3. SOFTWARES
# =========================================================================

async def search_software(
    session: AsyncSession,
    filters: Optional[SoftwareFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[ProductionSort] = None,
) -> SoftwareSearchResponse:
    t0 = time.perf_counter()
    filters = filters or SoftwareFilter()
    pagination = pagination or PaginationParams()
    sort = sort or ProductionSort()

    table = mv_canonical_software
    total = await production_repo.count_production(session, table, filters)
    rows = await production_repo.search_production(
        session, table, filters, sort, pagination
    )

    snippets = {}
    if filters.q and rows:
        ids = [r['canonical_id'] for r in rows]
        snippets = await production_repo.get_production_snippets(
            session, table, ids, filters.q, secondary_col='platform'
        )

    data = [
        SoftwareSummary(
            id=r['canonical_id'],
            title=r['title'],
            year=r.get('year'),
            platform=r.get('platform'),
            environment=r.get('environment'),
            code=r.get('code'),
            platform_authors=_authors(dict(r)),
            matches=snippets.get(r['canonical_id']),
        )
        for r in rows
    ]

    total_pages = math.ceil(total / pagination.per_page) if total > 0 else 0
    return SoftwareSearchResponse(
        data=data,
        pagination=Pagination(
            page=pagination.page,
            per_page=pagination.per_page,
            total_items=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_prev=pagination.page > 1,
        ),
        filters_applied=filters,
        sort=sort,
        meta=Meta(
            took_ms=int((time.perf_counter() - t0) * 1000),
            cached=False,
            timestamp=datetime.now(timezone.utc),
        ),
    )


async def get_software_detail(
    session: AsyncSession,
    software_id: UUID | str,
) -> SoftwareDetail:
    row = await production_repo.get_production_by_id(
        session, mv_canonical_software, software_id, natural_key_col='code'
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software '{software_id}' não encontrado",
        )
    r = dict(row)
    return SoftwareDetail(
        id=r['canonical_id'],
        title=r['title'],
        year=r.get('year'),
        platform=r.get('platform'),
        environment=r.get('environment'),
        code=r.get('code'),
        platform_authors=_authors(r),
        availability=r.get('availability'),
        financing=r.get('financing'),
    )


# =========================================================================
# 4. PATENTES
# =========================================================================

async def search_patents(
    session: AsyncSession,
    filters: Optional[PatentFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[ProductionSort] = None,
) -> PatentSearchResponse:
    t0 = time.perf_counter()
    filters = filters or PatentFilter()
    pagination = pagination or PaginationParams()
    sort = sort or ProductionSort()

    table = mv_canonical_patents
    total = await production_repo.count_production(session, table, filters)
    rows = await production_repo.search_production(
        session, table, filters, sort, pagination
    )

    snippets = {}
    if filters.q and rows:
        ids = [r['canonical_id'] for r in rows]
        snippets = await production_repo.get_production_snippets(
            session, table, ids, filters.q, secondary_col='category'
        )

    data = [
        PatentSummary(
            id=r['canonical_id'],
            title=r['title'],
            year=r.get('year'),
            category=r.get('category'),
            code=r.get('code'),
            platform_authors=_authors(dict(r)),
            matches=snippets.get(r['canonical_id']),
        )
        for r in rows
    ]

    total_pages = math.ceil(total / pagination.per_page) if total > 0 else 0
    return PatentSearchResponse(
        data=data,
        pagination=Pagination(
            page=pagination.page,
            per_page=pagination.per_page,
            total_items=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_prev=pagination.page > 1,
        ),
        filters_applied=filters,
        sort=sort,
        meta=Meta(
            took_ms=int((time.perf_counter() - t0) * 1000),
            cached=False,
            timestamp=datetime.now(timezone.utc),
        ),
    )


async def get_patent_detail(
    session: AsyncSession,
    patent_id: UUID | str,
) -> PatentDetail:
    row = await production_repo.get_production_by_id(
        session, mv_canonical_patents, patent_id, natural_key_col='code'
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patente '{patent_id}' não encontrada",
        )
    r = dict(row)
    return PatentDetail(
        id=r['canonical_id'],
        title=r['title'],
        year=r.get('year'),
        category=r.get('category'),
        code=r.get('code'),
        platform_authors=_authors(r),
        grant_date=r.get('grant_date'),
        deposit_date=r.get('deposit_date'),
        details=r.get('details'),
    )


# =========================================================================
# 5. PARTICIPAÇÃO EM EVENTOS
# =========================================================================

async def search_events(
    session: AsyncSession,
    filters: Optional[EventFilter] = None,
    pagination: Optional[PaginationParams] = None,
    sort: Optional[ProductionSort] = None,
) -> EventSearchResponse:
    t0 = time.perf_counter()
    filters = filters or EventFilter()
    pagination = pagination or PaginationParams()
    sort = sort or ProductionSort()

    table = mv_canonical_events
    total = await production_repo.count_production(session, table, filters)
    rows = await production_repo.search_production(
        session, table, filters, sort, pagination
    )

    snippets = {}
    if filters.q and rows:
        ids = [r['canonical_id'] for r in rows]
        snippets = await production_repo.get_production_snippets(
            session, table, ids, filters.q, secondary_col='event_name'
        )

    data = [
        EventSummary(
            id=r['canonical_id'],
            title=r['title'],
            event_name=r.get('event_name'),
            year=r.get('year'),
            nature=r.get('nature'),
            type_participation=r.get('type_participation'),
            platform_authors=_authors(dict(r)),
            matches=snippets.get(r['canonical_id']),
        )
        for r in rows
    ]

    total_pages = math.ceil(total / pagination.per_page) if total > 0 else 0
    return EventSearchResponse(
        data=data,
        pagination=Pagination(
            page=pagination.page,
            per_page=pagination.per_page,
            total_items=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_prev=pagination.page > 1,
        ),
        filters_applied=filters,
        sort=sort,
        meta=Meta(
            took_ms=int((time.perf_counter() - t0) * 1000),
            cached=False,
            timestamp=datetime.now(timezone.utc),
        ),
    )


async def get_event_detail(
    session: AsyncSession,
    event_id: UUID | str,
) -> EventDetail:
    row = await production_repo.get_production_by_id(
        session, mv_canonical_events, event_id
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participação em evento '{event_id}' não encontrada",
        )
    r = dict(row)
    return EventDetail(
        id=r['canonical_id'],
        title=r['title'],
        event_name=r.get('event_name'),
        year=r.get('year'),
        nature=r.get('nature'),
        type_participation=r.get('type_participation'),
        platform_authors=_authors(r),
        form_participation=r.get('form_participation'),
    )
