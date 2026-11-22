"""Rotas da Fase 2: revistas, bolsistas, termos e indicadores."""

import time
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import PaginationDep
from simcc.v2.errors import ApiError
from simcc.v2.repositories import indicators_repo
from simcc.v2.schemas.envelope import (
    ERROR_RESPONSES,
    LIST_ERROR_RESPONSES,
    DetailResponse,
)
from simcc.v2.schemas.indicators import (
    Magazine,
    MagazineFilter,
    MagazineListResponse,
    MagazineOptions,
    MagazineSort,
    ProductionMetricResponse,
    ScholarshipFilter,
    ScholarshipListResponse,
    ScholarshipOptions,
    ScholarshipSort,
    TermsParams,
    TermsResponse,
)
from simcc.v2.schemas.params import PaginationParams, build_pagination
from simcc.v2.schemas.production import ProductionBaseFilter
from simcc.v2.schemas.query import as_query, forbid_unknown_params
from simcc.v2.schemas.researcher import Sort
from simcc.v2.services.meta import build_meta

router = APIRouter()


def _query(model):
    return Annotated[model, Depends(as_query(model))]


# =========================================================================
# Revistas
# =========================================================================


@router.get(
    '/magazine',
    response_model=MagazineListResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[
        Depends(
            forbid_unknown_params(
                MagazineFilter, PaginationParams, MagazineSort, MagazineOptions
            )
        )
    ],
    tags=['Magazine v2'],
)
async def list_magazines(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    pagination: PaginationDep,
    filters: _query(MagazineFilter),
    sort: _query(MagazineSort),
    options: _query(MagazineOptions),
) -> MagazineListResponse:
    """Revistas com Qualis e JCR, buscáveis por nome e ISSN."""
    start = time.perf_counter()
    items, total = await indicators_repo.fetch_magazines(
        session, filters, pagination, sort
    )
    facets = None
    if options.facets:
        facets = await indicators_repo.fetch_magazine_facets(
            session, filters, options.facets, options.facet_limit
        )
    return MagazineListResponse(
        data=items,
        pagination=build_pagination(pagination, total),
        filters_applied=filters,
        sort=Sort.model_validate(sort),
        meta=await build_meta(session, start),
        facets=facets,
    )


@router.get(
    '/magazine/{magazine_id}',
    response_model=DetailResponse[Magazine],
    responses=ERROR_RESPONSES,
    tags=['Magazine v2'],
)
async def get_magazine(
    session: AsyncSession, magazine_id: UUID
) -> DetailResponse[Magazine]:
    start = time.perf_counter()
    magazine = await indicators_repo.fetch_magazine(session, magazine_id)
    if magazine is None:
        raise ApiError(404, 'Revista não encontrada.')
    return DetailResponse(data=magazine, meta=await build_meta(session, start))


# =========================================================================
# Bolsistas
# =========================================================================


@router.get(
    '/scholarship',
    response_model=ScholarshipListResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[
        Depends(
            forbid_unknown_params(
                ScholarshipFilter,
                PaginationParams,
                ScholarshipSort,
                ScholarshipOptions,
            )
        )
    ],
    tags=['Scholarship v2'],
)
async def list_scholarships(  # noqa: PLR0913, PLR0917
    session: AsyncSession,
    pagination: PaginationDep,
    filters: _query(ScholarshipFilter),
    sort: _query(ScholarshipSort),
    options: _query(ScholarshipOptions),
) -> ScholarshipListResponse:
    """Bolsas e auxílios (fomento) dos pesquisadores."""
    start = time.perf_counter()
    items, total = await indicators_repo.fetch_scholarships(
        session, filters, pagination, sort
    )
    facets = None
    if options.facets:
        facets = await indicators_repo.fetch_scholarship_facets(
            session, filters, options.facets, options.facet_limit
        )
    return ScholarshipListResponse(
        data=items,
        pagination=build_pagination(pagination, total),
        filters_applied=filters,
        sort=Sort.model_validate(sort),
        meta=await build_meta(session, start),
        facets=facets,
    )


# =========================================================================
# Termos do pesquisador
# =========================================================================


@router.get(
    '/researcher/{researcher_id}/terms',
    response_model=TermsResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[Depends(forbid_unknown_params(TermsParams))],
    tags=['Researcher v2'],
)
async def get_researcher_terms(
    session: AsyncSession,
    researcher_id: UUID,
    params: _query(TermsParams),
) -> TermsResponse:
    """Palavras mais frequentes nos títulos das produções do pesquisador
    (nuvem de palavras)."""
    start = time.perf_counter()
    terms = await indicators_repo.fetch_researcher_terms(
        session, researcher_id, params.limit
    )
    return TermsResponse(data=terms, meta=await build_meta(session, start))


# =========================================================================
# Indicadores
# =========================================================================

# Caminho com hífen → tipo do enum
_KIND_PATHS = {
    'article': 'article',
    'book': 'book',
    'book-chapter': 'book_chapter',
    'software': 'software',
    'patent': 'patent',
    'event': 'event',
    'research-project': 'research_project',
    'brand': 'brand',
    'guidance': 'guidance',
    'report': 'report',
    'magazine-text': 'magazine_text',
    'event-work': 'event_work',
}
KindPath = Literal[
    'article',
    'book',
    'book-chapter',
    'software',
    'patent',
    'event',
    'research-project',
    'brand',
    'guidance',
    'report',
    'magazine-text',
    'event-work',
]


@router.get(
    '/metrics/production/{kind}',
    response_model=ProductionMetricResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[Depends(forbid_unknown_params(ProductionBaseFilter))],
    tags=['Metrics v2'],
)
async def get_production_metric(
    session: AsyncSession,
    kind: Annotated[KindPath, Path(description='Tipo de produção')],
    filters: _query(ProductionBaseFilter),
) -> ProductionMetricResponse:
    """Série anual de produções de um tipo, com os mesmos filtros de
    `/v2/production/{kind}`."""
    start = time.perf_counter()
    kind_value = _KIND_PATHS[kind]
    series = await indicators_repo.fetch_production_series(
        session, kind_value, filters
    )
    return ProductionMetricResponse(
        kind=kind_value,
        data=series,
        filters_applied=filters,
        meta=await build_meta(session, start),
    )
