"""Roteador para produções científicas v2."""

import time

from fastapi import APIRouter, Depends

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import (
    ArticleFilterDep,
    ArticleSortDep,
    BookChapterFilterDep,
    BookFilterDep,
    EventFilterDep,
    PaginationDep,
    PatentFilterDep,
    ProductionOptionsDep,
    ProductionSortDep,
    ResearchProjectFilterDep,
    SearchCacheDep,
    SoftwareFilterDep,
)
from simcc.v2.repositories.search_tables import (
    mv_canonical_articles,
    mv_canonical_book_chapters,
    mv_canonical_books,
    mv_canonical_events,
    mv_canonical_patents,
    mv_canonical_research_projects,
    mv_canonical_software,
)
from simcc.v2.schemas.envelope import (
    ERROR_RESPONSES,
    LIST_ERROR_RESPONSES,
    DetailResponse,
)
from simcc.v2.schemas.params import PaginationParams
from simcc.v2.schemas.production import (
    ArticleDetail,
    ArticleFilter,
    ArticleSearchResponse,
    ArticleSort,
    BookChapterDetail,
    BookChapterFilter,
    BookChapterSearchResponse,
    BookDetail,
    BookFilter,
    BookSearchResponse,
    EventDetail,
    EventFilter,
    EventSearchResponse,
    PatentDetail,
    PatentFilter,
    PatentSearchResponse,
    ProductionOptions,
    ProductionSort,
    ResearchProjectDetail,
    ResearchProjectFilter,
    ResearchProjectSearchResponse,
    SoftwareDetail,
    SoftwareFilter,
    SoftwareSearchResponse,
)
from simcc.v2.schemas.query import forbid_unknown_params
from simcc.v2.services import (
    article_service,
    production_search_service,
    production_service,
)
from simcc.v2.services.meta import build_meta

router = APIRouter(tags=['Produções v2'])


def _known_params(filters: type, sort: type):
    """Rejeita (422) parâmetros de query que a listagem não declara."""
    return Depends(
        forbid_unknown_params(
            filters, sort, PaginationParams, ProductionOptions
        )
    )


# =========================================================================
# ARTIGOS
# =========================================================================

@router.get(
    '/production/article',
    response_model=ArticleSearchResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[_known_params(ArticleFilter, ArticleSort)],
    summary='Busca e listagem paginada de artigos científicos',
)
async def list_articles(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    cache: SearchCacheDep,
    filters: ArticleFilterDep,
    pagination: PaginationDep,
    sort: ArticleSortDep,
    options: ProductionOptionsDep,
) -> ArticleSearchResponse:
    """Retorna lista paginada de artigos com busca textual ponderada."""
    return await production_search_service.search_production(
        article_service.search_articles,
        ArticleSearchResponse,
        mv_canonical_articles,
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
        cache=cache,
    )


@router.get(
    '/production/article/{article_id:path}',
    response_model=DetailResponse[ArticleDetail],
    responses=ERROR_RESPONSES,
    summary='Dossiê detalhado de um artigo científico',
)
async def get_article(
    session: AsyncSession,
    article_id: str,
) -> DetailResponse[ArticleDetail]:
    """Retorna o detalhe do artigo pelo ID canônico (UUID) ou DOI."""
    start = time.perf_counter()
    item = await article_service.get_article_detail(
        session=session,
        article_id=article_id,
    )
    return DetailResponse(
        data=item, meta=await build_meta(session, start)
    )


# =========================================================================
# 1. LIVROS
# =========================================================================

@router.get(
    '/production/book',
    response_model=BookSearchResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[_known_params(BookFilter, ProductionSort)],
    summary='Busca e listagem paginada de livros',
)
async def list_books(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    cache: SearchCacheDep,
    filters: BookFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
    options: ProductionOptionsDep,
) -> BookSearchResponse:
    """Retorna lista paginada de livros com busca textual e filtros."""
    return await production_search_service.search_production(
        production_service.search_books,
        BookSearchResponse,
        mv_canonical_books,
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
        cache=cache,
    )


@router.get(
    '/production/book/{book_id:path}',
    response_model=DetailResponse[BookDetail],
    responses=ERROR_RESPONSES,
    summary='Dossiê detalhado de livro',
)
async def get_book(
    session: AsyncSession,
    book_id: str,
) -> DetailResponse[BookDetail]:
    """Retorna detalhes de um livro pelo ID canônico ou ISBN."""
    start = time.perf_counter()
    item = await production_service.get_book_detail(
        session=session,
        book_id=book_id,
    )
    return DetailResponse(
        data=item, meta=await build_meta(session, start)
    )


# =========================================================================
# 2. CAPÍTULOS DE LIVROS
# =========================================================================

@router.get(
    '/production/book-chapter',
    response_model=BookChapterSearchResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[_known_params(BookChapterFilter, ProductionSort)],
    summary='Busca e listagem paginada de capítulos de livros',
)
async def list_book_chapters(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    cache: SearchCacheDep,
    filters: BookChapterFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
    options: ProductionOptionsDep,
) -> BookChapterSearchResponse:
    """Retorna lista paginada de capítulos de livros com filtros."""
    return await production_search_service.search_production(
        production_service.search_book_chapters,
        BookChapterSearchResponse,
        mv_canonical_book_chapters,
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
        cache=cache,
    )


@router.get(
    '/production/book-chapter/{chapter_id:path}',
    response_model=DetailResponse[BookChapterDetail],
    responses=ERROR_RESPONSES,
    summary='Dossiê detalhado de capítulo de livro',
)
async def get_book_chapter(
    session: AsyncSession,
    chapter_id: str,
) -> DetailResponse[BookChapterDetail]:
    """Retorna detalhes de um capítulo pelo ID canônico ou ISBN."""
    start = time.perf_counter()
    item = await production_service.get_book_chapter_detail(
        session=session,
        chapter_id=chapter_id,
    )
    return DetailResponse(
        data=item, meta=await build_meta(session, start)
    )


# =========================================================================
# 3. SOFTWARES
# =========================================================================

@router.get(
    '/production/software',
    response_model=SoftwareSearchResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[_known_params(SoftwareFilter, ProductionSort)],
    summary='Busca e listagem paginada de softwares',
)
async def list_software(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    cache: SearchCacheDep,
    filters: SoftwareFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
    options: ProductionOptionsDep,
) -> SoftwareSearchResponse:
    """Retorna lista paginada de softwares com filtros."""
    return await production_search_service.search_production(
        production_service.search_software,
        SoftwareSearchResponse,
        mv_canonical_software,
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
        cache=cache,
    )


@router.get(
    '/production/software/{software_id:path}',
    response_model=DetailResponse[SoftwareDetail],
    responses=ERROR_RESPONSES,
    summary='Dossiê detalhado de software',
)
async def get_software(
    session: AsyncSession,
    software_id: str,
) -> DetailResponse[SoftwareDetail]:
    """Retorna detalhes de um software pelo ID canônico ou código."""
    start = time.perf_counter()
    item = await production_service.get_software_detail(
        session=session,
        software_id=software_id,
    )
    return DetailResponse(
        data=item, meta=await build_meta(session, start)
    )


# =========================================================================
# 4. PATENTES
# =========================================================================

@router.get(
    '/production/patent',
    response_model=PatentSearchResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[_known_params(PatentFilter, ProductionSort)],
    summary='Busca e listagem paginada de patentes',
)
async def list_patents(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    cache: SearchCacheDep,
    filters: PatentFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
    options: ProductionOptionsDep,
) -> PatentSearchResponse:
    """Retorna lista paginada de patentes com filtros."""
    return await production_search_service.search_production(
        production_service.search_patents,
        PatentSearchResponse,
        mv_canonical_patents,
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
        cache=cache,
    )


@router.get(
    '/production/patent/{patent_id:path}',
    response_model=DetailResponse[PatentDetail],
    responses=ERROR_RESPONSES,
    summary='Dossiê detalhado de patente',
)
async def get_patent(
    session: AsyncSession,
    patent_id: str,
) -> DetailResponse[PatentDetail]:
    """Retorna detalhes de uma patente pelo ID canônico ou código."""
    start = time.perf_counter()
    item = await production_service.get_patent_detail(
        session=session,
        patent_id=patent_id,
    )
    return DetailResponse(
        data=item, meta=await build_meta(session, start)
    )


# =========================================================================
# 5. PARTICIPAÇÃO EM EVENTOS
# =========================================================================

@router.get(
    '/production/event',
    response_model=EventSearchResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[_known_params(EventFilter, ProductionSort)],
    summary='Busca e listagem paginada de participação em eventos',
)
async def list_events(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    cache: SearchCacheDep,
    filters: EventFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
    options: ProductionOptionsDep,
) -> EventSearchResponse:
    """Retorna lista paginada de eventos com filtros."""
    return await production_search_service.search_production(
        production_service.search_events,
        EventSearchResponse,
        mv_canonical_events,
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
        cache=cache,
    )


@router.get(
    '/production/event/{event_id:path}',
    response_model=DetailResponse[EventDetail],
    responses=ERROR_RESPONSES,
    summary='Dossiê detalhado de participação em evento',
)
async def get_event(
    session: AsyncSession,
    event_id: str,
) -> DetailResponse[EventDetail]:
    """Retorna detalhes de uma participação em evento pelo ID canônico."""
    start = time.perf_counter()
    item = await production_service.get_event_detail(
        session=session,
        event_id=event_id,
    )
    return DetailResponse(
        data=item, meta=await build_meta(session, start)
    )


# =========================================================================
# 6. PROJETOS DE PESQUISA
# =========================================================================

@router.get(
    '/production/research-project',
    response_model=ResearchProjectSearchResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[_known_params(ResearchProjectFilter, ProductionSort)],
    summary='Busca e listagem paginada de projetos de pesquisa',
)
async def list_research_projects(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    cache: SearchCacheDep,
    filters: ResearchProjectFilterDep,
    pagination: PaginationDep,
    sort: ProductionSortDep,
    options: ProductionOptionsDep,
) -> ResearchProjectSearchResponse:
    """Retorna lista paginada de projetos de pesquisa com filtros."""
    return await production_search_service.search_production(
        production_service.search_research_projects,
        ResearchProjectSearchResponse,
        mv_canonical_research_projects,
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
        cache=cache,
    )


@router.get(
    '/production/research-project/{project_id:path}',
    response_model=DetailResponse[ResearchProjectDetail],
    responses=ERROR_RESPONSES,
    summary='Dossiê detalhado de projeto de pesquisa',
)
async def get_research_project(
    session: AsyncSession,
    project_id: str,
) -> DetailResponse[ResearchProjectDetail]:
    """Retorna detalhes de um projeto de pesquisa pelo ID canônico."""
    start = time.perf_counter()
    item = await production_service.get_research_project_detail(
        session=session,
        project_id=project_id,
    )
    return DetailResponse(
        data=item, meta=await build_meta(session, start)
    )
