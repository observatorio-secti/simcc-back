"""Rotas da Fase 2: revistas, bolsistas, termos e indicadores."""

import time
from http import HTTPStatus
from typing import Annotated, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request

from simcc.core.dependencies import AsyncSession
from simcc.v2.dependencies import PaginationDep
from simcc.v2.errors import ApiError, unknown_parameter
from simcc.v2.repositories import indicators_repo
from simcc.v2.schemas.envelope import (
    ERROR_RESPONSES,
    LIST_ERROR_RESPONSES,
    DetailResponse,
    ErrorDetail,
)
from simcc.v2.schemas.indicators import (
    Magazine,
    MagazineFilter,
    MagazineListResponse,
    MagazineOptions,
    MagazineSort,
    ProductionMetricFilter,
    ProductionMetricResponse,
    ScholarshipFilter,
    ScholarshipListResponse,
    ScholarshipOptions,
    ScholarshipSort,
    TermsParams,
    TermsResponse,
)
from simcc.v2.schemas.params import PaginationParams, build_pagination
from simcc.v2.schemas.production import (
    ArticleFilter,
    BookChapterFilter,
    BookFilter,
    BrandFilter,
    EventFilter,
    EventWorkFilter,
    GuidanceFilter,
    MagazineTextFilter,
    PatentFilter,
    ProductionBaseFilter,
    ReportFilter,
    ResearchProjectFilter,
    SoftwareFilter,
)
from simcc.v2.schemas.query import (
    as_query,
    forbid_unknown_params,
    known_param_names,
)
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


_KIND_FILTER_MODELS: dict[str, type[ProductionBaseFilter]] = {
    'article': ArticleFilter,
    'book': BookFilter,
    'book_chapter': BookChapterFilter,
    'software': SoftwareFilter,
    'patent': PatentFilter,
    'event': EventFilter,
    'research_project': ResearchProjectFilter,
    'brand': BrandFilter,
    'guidance': GuidanceFilter,
    'report': ReportFilter,
    'magazine_text': MagazineTextFilter,
    'event_work': EventWorkFilter,
}


def _validate_metric_params(kind: KindPath, request: Request) -> None:
    """Rejeita (422) parâmetros não aceitos pelo `{kind}` consultado."""
    kind_value = _KIND_PATHS[kind]
    allowed_params = known_param_names(_KIND_FILTER_MODELS[kind_value]) | {
        'group_by'
    }
    for param_name in request.query_params:
        if param_name not in allowed_params:
            raise unknown_parameter(param_name)


@router.get(
    '/metrics/production/{kind}',
    response_model=ProductionMetricResponse,
    responses=LIST_ERROR_RESPONSES,
    dependencies=[Depends(_validate_metric_params)],
    tags=['Metrics v2'],
)
async def get_production_metric(
    session: AsyncSession,
    kind: Annotated[KindPath, Path(description='Tipo de produção')],
    filters: _query(ProductionMetricFilter),
    group_by: Annotated[
        Optional[str],
        Query(
            description=(
                'Dimensão para quebra por categoria dentro de cada ano '
                '(ex.: qualis em article; nature/status em guidance; '
                'nature/type_participation em event; status/nature em '
                'research-project)'
            )
        ),
    ] = None,
) -> ProductionMetricResponse:
    """Série anual de produções de um tipo, com os mesmos filtros de
    `/v2/production/{kind}` e agrupamento opcional (`group_by`)."""
    start = time.perf_counter()
    kind_value = _KIND_PATHS[kind]

    allowed_groups = indicators_repo.ALLOWED_GROUP_BY.get(kind_value, ())
    if group_by is not None and group_by not in allowed_groups:
        allowed_desc = (
            ', '.join(allowed_groups) if allowed_groups else 'nenhum'
        )
        raise ApiError(
            HTTPStatus.UNPROCESSABLE_CONTENT,
            f"group_by='{group_by}' não é suportado para '{kind}'. "
            f'Valores permitidos: {allowed_desc}',
            code='invalid_group_by',
            details=[
                ErrorDetail(
                    field='group_by',
                    message=f'Dimensão não suportada para {kind}',
                    type='invalid_group_by',
                    input=group_by,
                )
            ],
        )

    filter_cls = _KIND_FILTER_MODELS[kind_value]
    kind_filters = filter_cls.model_validate(
        {k: getattr(filters, k) for k in filter_cls.model_fields}
    )

    series = await indicators_repo.fetch_production_series(
        session, kind_value, kind_filters, group_by=group_by
    )
    return ProductionMetricResponse(
        kind=kind_value,
        group_by=group_by,
        data=series,
        filters_applied=kind_filters,
        meta=await build_meta(session, start),
    )
