"""Roteador para produções científicas v2 (Artigos)."""


from fastapi import APIRouter

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import (
    ArticleFilterDep,
    ArticleSortDep,
    PaginationDep,
)
from simcc.v2.schemas.production import (
    ArticleDetail,
    ArticleSearchResponse,
)
from simcc.v2.services import article_service

router = APIRouter(tags=['Produções v2'])


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
