"""Roteador para produções científicas v2."""

from fastapi import APIRouter

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import (
    ArticleFilterDep,
    ArticleSortDep,
    BookChapterFilterDep,
    BookFilterDep,
    EventFilterDep,
    PaginationDep,
    PatentFilterDep,
    ProductionSortDep,
    SoftwareFilterDep,
)
from simcc.v2.schemas.production import (
    ArticleDetail,
    ArticleSearchResponse,
    BookChapterDetail,
    BookChapterSearchResponse,
    BookDetail,
    BookSearchResponse,
    EventDetail,
    EventSearchResponse,
    PatentDetail,
    PatentSearchResponse,
    SoftwareDetail,
    SoftwareSearchResponse,
)
from simcc.v2.services import article_service, production_service

router = APIRouter(tags=['Produções v2'])


# =========================================================================
# ARTIGOS
# =========================================================================

@router.get(
    '/production/article',
    response_model=ArticleSearchResponse,
    summary='Busca e listagem paginada de artigos científicos',
)
async def list_articles(
    session: AsyncSession,
    filters: ArticleFilterDep,
    pagination: PaginationDep,
    sort: ArticleSortDep,
) -> ArticleSearchResponse:
    """Retorna lista paginada de artigos com busca textual ponderada."""
    return await article_service.search_articles(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
    )


@router.get(
    '/production/article/{article_id:path}',
    response_model=ArticleDetail,
    summary='Dossiê detalhado de um artigo científico',
)
async def get_article(
    session: AsyncSession,
    article_id: str,
) -> ArticleDetail:
    """Retorna o detalhe do artigo pelo ID canônico (UUID) ou DOI."""
    return await article_service.get_article_detail(
        session=session,
        article_id=article_id,
    )


# =========================================================================
# 1. LIVROS
# =========================================================================

@router.get(
    '/production/book',
    response_model=BookSearchResponse,
    summary='Busca e listagem paginada de livros',
)
async def list_books(
    session: AsyncSession,
    filters: BookFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
) -> BookSearchResponse:
    """Retorna lista paginada de livros com busca textual e filtros."""
    return await production_service.search_books(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
    )


@router.get(
    '/production/book/{book_id:path}',
    response_model=BookDetail,
    summary='Dossiê detalhado de livro',
)
async def get_book(
    session: AsyncSession,
    book_id: str,
) -> BookDetail:
    """Retorna detalhes de um livro pelo ID canônico ou ISBN."""
    return await production_service.get_book_detail(
        session=session,
        book_id=book_id,
    )


# =========================================================================
# 2. CAPÍTULOS DE LIVROS
# =========================================================================

@router.get(
    '/production/book-chapter',
    response_model=BookChapterSearchResponse,
    summary='Busca e listagem paginada de capítulos de livros',
)
async def list_book_chapters(
    session: AsyncSession,
    filters: BookChapterFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
) -> BookChapterSearchResponse:
    """Retorna lista paginada de capítulos de livros com filtros."""
    return await production_service.search_book_chapters(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
    )


@router.get(
    '/production/book-chapter/{chapter_id:path}',
    response_model=BookChapterDetail,
    summary='Dossiê detalhado de capítulo de livro',
)
async def get_book_chapter(
    session: AsyncSession,
    chapter_id: str,
) -> BookChapterDetail:
    """Retorna detalhes de um capítulo pelo ID canônico ou ISBN."""
    return await production_service.get_book_chapter_detail(
        session=session,
        chapter_id=chapter_id,
    )


# =========================================================================
# 3. SOFTWARES
# =========================================================================

@router.get(
    '/production/software',
    response_model=SoftwareSearchResponse,
    summary='Busca e listagem paginada de softwares',
)
async def list_software(
    session: AsyncSession,
    filters: SoftwareFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
) -> SoftwareSearchResponse:
    """Retorna lista paginada de softwares com filtros."""
    return await production_service.search_software(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
    )


@router.get(
    '/production/software/{software_id:path}',
    response_model=SoftwareDetail,
    summary='Dossiê detalhado de software',
)
async def get_software(
    session: AsyncSession,
    software_id: str,
) -> SoftwareDetail:
    """Retorna detalhes de um software pelo ID canônico ou código."""
    return await production_service.get_software_detail(
        session=session,
        software_id=software_id,
    )


# =========================================================================
# 4. PATENTES
# =========================================================================

@router.get(
    '/production/patent',
    response_model=PatentSearchResponse,
    summary='Busca e listagem paginada de patentes',
)
async def list_patents(
    session: AsyncSession,
    filters: PatentFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
) -> PatentSearchResponse:
    """Retorna lista paginada de patentes com filtros."""
    return await production_service.search_patents(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
    )


@router.get(
    '/production/patent/{patent_id:path}',
    response_model=PatentDetail,
    summary='Dossiê detalhado de patente',
)
async def get_patent(
    session: AsyncSession,
    patent_id: str,
) -> PatentDetail:
    """Retorna detalhes de uma patente pelo ID canônico ou código."""
    return await production_service.get_patent_detail(
        session=session,
        patent_id=patent_id,
    )


# =========================================================================
# 5. PARTICIPAÇÃO EM EVENTOS
# =========================================================================

@router.get(
    '/production/event',
    response_model=EventSearchResponse,
    summary='Busca e listagem paginada de participação em eventos',
)
async def list_events(
    session: AsyncSession,
    filters: EventFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
) -> EventSearchResponse:
    """Retorna lista paginada de eventos com filtros."""
    return await production_service.search_events(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
    )


@router.get(
    '/production/event/{event_id:path}',
    response_model=EventDetail,
    summary='Dossiê detalhado de participação em evento',
)
async def get_event(
    session: AsyncSession,
    event_id: str,
) -> EventDetail:
    """Retorna detalhes de uma participação em evento pelo ID canônico."""
    return await production_service.get_event_detail(
        session=session,
        event_id=event_id,
    )
