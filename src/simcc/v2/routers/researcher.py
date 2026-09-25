"""Router para busca e listagem de pesquisadores v2."""

from fastapi import APIRouter, Depends

from simcc.core.dependencies import AsyncSession
from simcc.v2.schemas.filters import (
    ResearcherFilter,
    get_researcher_filter,
    validate_unknown_researcher_params,
)
from simcc.v2.schemas.params import (
    PaginationParams,
    SearchOptions,
    SortParams,
    get_search_options,
)
from simcc.v2.schemas.researcher import SearchResponse
from simcc.v2.services import researcher_service

router = APIRouter(tags=['Researcher v2'])


@router.get(
    '/researcher',
    response_model=SearchResponse,
    dependencies=[Depends(validate_unknown_researcher_params)],
)
async def list_researchers(
    session: AsyncSession,
    filters: ResearcherFilter = Depends(get_researcher_filter),
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    options: SearchOptions = Depends(get_search_options),
) -> SearchResponse:
    """Retorna lista paginada de pesquisadores com filtros e ordenação."""
    return await researcher_service.search_researchers(
        session=session,
        filters=filters,
        pagination=pagination,
        sort=sort,
        options=options,
    )
