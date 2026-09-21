from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import Depends, Query


def pagination_params(
    page: Annotated[int, Query(ge=1, description='Número da página')] = 1,
    per_page: Annotated[
        int, Query(ge=1, le=100, description='Itens por página')
    ] = 20,
) -> dict[str, int]:
    return {'page': page, 'per_page': per_page}


def sort_params(
    sort_by: Annotated[
        str, Query(alias='by', description='Campo de ordenação')
    ] = 'name',
    sort_order: Annotated[
        Literal['asc', 'desc'],
        Query(alias='order', description='Direção da ordenação'),
    ] = 'asc',
) -> dict[str, str]:
    return {'by': sort_by, 'order': sort_order}


def common_filter_params(
    q: Annotated[
        str | None,
        Query(description='Termo para busca semântica ou textual unificada'),
    ] = None,
    query: Annotated[
        str | None,
        Query(include_in_schema=False, description='Alias para q'),
    ] = None,
    year_start: Annotated[
        int | None, Query(ge=1900, le=2100, description='Ano inicial')
    ] = None,
    year_end: Annotated[
        int | None, Query(ge=1900, le=2100, description='Ano final')
    ] = None,
    institution_id: Annotated[
        UUID | None, Query(description='ID da instituição')
    ] = None,
) -> dict[str, Any]:
    raw_search = q if q is not None else query
    clean_q = raw_search.strip() if raw_search and raw_search.strip() else None
    return {
        'q': clean_q,
        'year_start': year_start,
        'year_end': year_end,
        'institution_id': institution_id,
    }


def researcher_filter_params(
    common: Annotated[dict[str, Any], Depends(common_filter_params)],
    graduate_program_id: Annotated[
        UUID | None,
        Query(description='ID do programa de pós-graduação'),
    ] = None,
) -> dict[str, Any]:
    filters = dict(common)
    filters['graduate_program_id'] = graduate_program_id
    return filters


def researcher_query_params(
    filters: Annotated[dict[str, Any], Depends(researcher_filter_params)],
    pagination: Annotated[dict[str, int], Depends(pagination_params)],
    sort: Annotated[dict[str, str], Depends(sort_params)],
) -> dict[str, Any]:
    return {
        'filters': filters,
        'pagination': pagination,
        'sort': sort,
    }
