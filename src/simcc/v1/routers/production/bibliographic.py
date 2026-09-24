from fastapi import APIRouter, Depends

from simcc.core.dependencies import (
    AsyncSession,
    CurrentUser,
    Filters,
)
from simcc.v1.schemas import DefaultFilters, QualisOptions
from simcc.v1.schemas.production import (
    ArticleProduction,
    BookChapterProduction,
    BookProduction,
    Magazine,
    MagazineFilters,
    PapersProduction,
    RecentlyUpdatedArticle,
)
from simcc.v1.services import production_service

router = APIRouter(tags=['Production - Bibliographic'])


@router.get('/production/book', response_model=list[BookProduction])
@router.get('/book_production_researcher', include_in_schema=False)
async def list_book_production(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_book(session, filters)


@router.get(
    '/production/book-chapter',
    response_model=list[BookChapterProduction],
)
@router.get(
    '/book_chapter_production_researcher',
    include_in_schema=False,
)
async def list_book_chapter_production(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_book_chapter(session, filters)


@router.get('/outstanding_articles', include_in_schema=False)
async def list_outstanding_articles(
    session: AsyncSession,
):
    articles = await production_service.list_bibliographic_production(
        session,
        DefaultFilters(type='ARTICLE', distinct=1, year=20),
        None,
        None,
        None,
    )
    return articles


@router.get('/production/article', response_model=list[ArticleProduction])
@router.get('/bibliographic_production_article', include_in_schema=False)
@router.get('/bibliographic_production_researcher', include_in_schema=False)
async def list_bibliographic_production(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
    qualis: QualisOptions | str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.type = 'ARTICLE'
    filters.star = current_user if filters.star else None

    return await production_service.list_bibliographic_production(
        session, filters, qualis
    )


@router.get('/production/paper', response_model=list[PapersProduction])
@router.get('/researcher_production/papers_magazine', include_in_schema=False)
async def list_papers_magazine(
    session: AsyncSession,
    current_user: CurrentUser,
    filters: Filters,
    terms: str | None = None,
):
    filters.term = terms if terms else filters.term
    filters.star = current_user if filters.star else None

    return await production_service.list_papers_magazine(session, filters)


@router.get('/magazine', response_model=list[Magazine])
async def list_magazine(
    session: AsyncSession,
    filters: MagazineFilters = Depends(),
):
    return await production_service.list_magazine(session, filters)


@router.get('/recently_updated', response_model=list[RecentlyUpdatedArticle])
async def list_recently_updated(
    session: AsyncSession,
    filters: Filters,
    university: str | None = None,
):
    filters.institution = university if university else None

    return await production_service.list_recently_updated(session, filters)
